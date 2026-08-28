from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.entities import (
    AuditEvent,
    BriefStatus,
    CommandBrief,
    DoctrineEntry,
    ExecutionState,
    GatewayRequest,
    GatewayStatus,
    Mission,
    MissionArtifact,
    MissionStatus,
    Project,
    ProjectStatus,
    Specialist,
)
from app.schemas.gateway import GatewayInput
from app.services.capabilities import capability_ready, discover_capabilities
from app.services.command_registry import CommandSpec, resolve_command
from app.services.deployment import assess_production_readiness
from app.services.mission_control import dependencies_satisfied, dispatch_mission, dispatch_next


STATE_KEY = "canonical"
PROTECTED_STATE_FIELDS = frozenset(
    {
        "approved_decisions",
        "locked_assets",
        "rollback_reference",
        "production_acceptance",
        "delivered_artifact_ids",
    }
)
ACTIVE_MISSION_STATES = frozenset(
    {
        MissionStatus.queued,
        MissionStatus.dispatched,
        MissionStatus.running,
        MissionStatus.verification_pending,
        MissionStatus.recovering,
    }
)
SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|token|secret|password)\s*[:=]\s*\S{8,}", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{16,}={0,2}\b", re.IGNORECASE),
)


def contains_potential_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in SECRET_PATTERNS)


def default_execution_state() -> dict:
    resource = files("app.resources").joinpath("execution_state.default.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def get_execution_state(db: Session, settings: Settings) -> ExecutionState:
    item = db.get(ExecutionState, settings.gateway_state_key or STATE_KEY)
    if item is None:
        item = ExecutionState(
            key=settings.gateway_state_key or STATE_KEY,
            payload=default_execution_state(),
            updated_by="system",
        )
        db.add(item)
        db.flush()
    return item


def patch_execution_state(
    db: Session,
    settings: Settings,
    *,
    expected_revision: int,
    changes: dict[str, Any],
    actor_role: str,
) -> ExecutionState:
    item = get_execution_state(db, settings)
    if item.revision != expected_revision:
        raise HTTPException(status_code=409, detail="Execution state revision has changed; refresh before updating")
    protected = set(changes) & PROTECTED_STATE_FIELDS
    if protected and actor_role != "founder":
        raise HTTPException(
            status_code=403,
            detail="Founder authority is required to change approved decisions, locked assets, or rollback authority",
        )
    payload = dict(item.payload)
    payload.update(changes)
    item.payload = payload
    item.revision += 1
    item.updated_by = actor_role
    db.add(
        AuditEvent(
            event_type="gateway.execution_state_updated",
            resource_type="execution_state",
            resource_id=None,
            metadata_json={"state_key": item.key, "revision": item.revision, "fields": sorted(changes)},
        )
    )
    db.commit()
    db.refresh(item)
    return item


def _choose_project(db: Session, explicit_project_id: str | None, state: ExecutionState) -> Project | None:
    if explicit_project_id:
        item = db.get(Project, explicit_project_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return item
    state_project = state.payload.get("active_project")
    if state_project:
        item = db.scalar(select(Project).where(Project.slug == str(state_project)))
        if item is not None:
            return item
    return db.scalar(
        select(Project)
        .where(Project.status == ProjectStatus.active)
        .order_by(Project.updated_at.desc(), Project.created_at.desc())
    )


def _active_brief(db: Session, project: Project | None) -> CommandBrief | None:
    if project is None:
        return None
    return db.scalar(
        select(CommandBrief)
        .where(
            CommandBrief.project_id == project.id,
            CommandBrief.status.in_([BriefStatus.active, BriefStatus.approved]),
        )
        .order_by(CommandBrief.updated_at.desc(), CommandBrief.created_at.desc())
    )


def _mission_counts(missions: Sequence[Mission]) -> dict[str, int]:
    counts = {status.value: 0 for status in MissionStatus}
    for item in missions:
        counts[item.status.value] += 1
    return counts


def build_context_packet(
    db: Session,
    settings: Settings,
    *,
    project_id: str | None = None,
    repository_root: Path | None = None,
) -> dict:
    state = get_execution_state(db, settings)
    project = _choose_project(db, project_id, state)
    brief = _active_brief(db, project)
    project_missions = (
        db.scalars(
            select(Mission)
            .join(CommandBrief, Mission.command_brief_id == CommandBrief.id)
            .where(CommandBrief.project_id == project.id)
            .order_by(Mission.priority.desc(), Mission.created_at)
        ).all()
        if project is not None
        else []
    )
    next_mission = next(
        (
            item
            for item in project_missions
            if item.status == MissionStatus.queued
            and item.command_brief.status in {BriefStatus.approved, BriefStatus.active}
            and dependencies_satisfied(db, item)
        ),
        None,
    )
    capabilities = discover_capabilities(settings, repository_root)
    doctrine = db.scalars(
        select(DoctrineEntry).where(DoctrineEntry.is_active.is_(True)).order_by(DoctrineEntry.key)
    ).all()
    locked_assets = list(state.payload.get("locked_assets", []))
    project_truth = project.source_of_truth if project is not None else {}
    if isinstance(project_truth, dict):
        for locator in project_truth.get("locked_assets", []):
            if locator not in locked_assets:
                locked_assets.append(locator)
    last_validated_commit = settings.last_validated_commit or state.payload.get("last_validated_commit")
    return {
        "schema_version": 1,
        "state_key": state.key,
        "state_revision": state.revision,
        "active_project": (
            {"id": project.id, "slug": project.slug, "name": project.name, "status": project.status.value}
            if project
            else None
        ),
        "current_milestone": state.payload.get("current_milestone"),
        "current_objective": brief.objective if brief else state.payload.get("current_objective"),
        "active_command_brief": (
            {"id": brief.id, "title": brief.title, "status": brief.status.value, "authority": brief.authority}
            if brief
            else None
        ),
        "approved_decisions": state.payload.get("approved_decisions", []),
        "locked_assets": locked_assets,
        "canonical_sources": project_truth,
        "work_in_progress": [
            {"id": item.id, "title": item.title, "status": item.status.value, "specialist": item.specialist_key}
            for item in project_missions
            if item.status in ACTIVE_MISSION_STATES
        ],
        "completed_work": [
            {
                "id": item.id,
                "title": item.title,
                "verified_at": item.verified_at.isoformat() if item.verified_at else None,
            }
            for item in project_missions
            if item.status == MissionStatus.verified
        ],
        "blocked_work": [
            {"id": item.id, "title": item.title, "status": item.status.value, "root_cause": item.root_cause}
            for item in project_missions
            if item.status in {MissionStatus.failed, MissionStatus.blocked, MissionStatus.stalled, MissionStatus.verification_failed}
        ],
        "next_executable_work": (
            {"id": next_mission.id, "title": next_mission.title, "specialist": next_mission.specialist_key}
            if next_mission
            else state.payload.get("next_executable_work")
        ),
        "assigned_agents": sorted({item.specialist_key for item in project_missions if item.status in ACTIVE_MISSION_STATES}),
        "mission_counts": _mission_counts(project_missions),
        "deployment_state": state.payload.get("deployment_state", {}),
        "environment_state": {
            **state.payload.get("environment_state", {}),
            "environment": settings.env,
            "release": settings.release_id,
        },
        "services": [{"service": item["service"], "status": item["status"]} for item in capabilities],
        "doctrine": [
            {"key": item.key, "title": item.title, "category": item.category, "version": item.version}
            for item in doctrine
        ],
        "last_validated_commit": last_validated_commit,
        "last_deployment": state.payload.get("last_deployment"),
        "rollback_reference": settings.rollback_reference or state.payload.get("rollback_reference"),
    }


def _specialist_authority(item: Specialist) -> dict:
    return {
        "key": item.key,
        "name": item.name,
        "responsibility": item.responsibility,
        "permissions": list(item.permissions),
        "standards": list(item.validation_requirements),
    }


def assemble_specialists(
    db: Session,
    raw_input: str,
    command: CommandSpec | None,
    *,
    operating_mode: str = "founder",
) -> dict:
    normalized = raw_input.casefold()
    active = {item.key: item for item in db.scalars(select(Specialist).where(Specialist.is_active.is_(True))).all()}
    security_terms = {"security", "secret", "credential", "auth", "permission", "database", "production"}
    engineering_terms = {"repo", "code", "build", "test", "deploy", "railway", "github", "hostinger", "ci", "branch"}
    provider_terms = {"model", "provider", "openrouter", "litellm", "routing", "architecture"}
    provenance_terms = {"canonical", "source of truth", "doctrine", "provenance", "audit", "locked"}

    security = bool(security_terms & set(normalized.split())) or bool(command and command.key in {"deploy", "approve_lock"})
    if any(term in normalized for term in provider_terms):
        lead = "arc"
    elif any(term in normalized for term in provenance_terms):
        lead = "griot"
    elif security and not any(term in normalized for term in engineering_terms):
        lead = "invictus"
    else:
        lead = "al"
    if lead not in active:
        lead = "al" if "al" in active else next(iter(active), "mission_control")

    support_candidates: list[str] = []
    if any(term in normalized for term in engineering_terms) and lead != "al":
        support_candidates.append("al")
    if any(term in normalized for term in provider_terms) and lead != "arc":
        support_candidates.append("arc")
    if security and lead != "invictus":
        support_candidates.append("invictus")
    if any(term in normalized for term in provenance_terms) and lead != "griot":
        support_candidates.append("griot")
    if operating_mode == "client" and lead != "liv":
        support_candidates.append("liv")
    support = [key for key in dict.fromkeys(support_candidates) if key in active and key != lead]
    reviewer = "invictus" if security and "invictus" in active and lead != "invictus" else "griot"
    if reviewer not in active or reviewer == lead:
        reviewer = "griot" if "griot" in active and lead != "griot" else lead
    support = [key for key in support if key != reviewer]
    requirements = list(active[lead].validation_requirements) if lead in active else []
    requirements.extend(
        [
            "material_evidence_recorded",
            "self_contained_handoff",
            "copy_ready_delivery",
            "canonical_state_updated",
            "next_action_explicit",
        ]
    )
    return {
        "lead_specialist": lead,
        "supporting_specialists": support,
        "validation_specialist": reviewer,
        "lead_authority": _specialist_authority(active[lead]) if lead in active else None,
        "supporting_authorities": [_specialist_authority(active[key]) for key in support],
        "validation_authority": _specialist_authority(active[reviewer]) if reviewer in active else None,
        "security_implications": security,
        "operational_implications": bool(command and command.action in {"dispatch_staged", "dispatch_next", "deploy_staging", "approve_reference"}),
        "canonical_sources_required": ["execution_state", "active_project", "active_command_brief", "doctrine_registry"],
        "acceptance_criteria": list(dict.fromkeys(requirements)),
        "operating_mode": operating_mode,
        "experience_sequence": ["intent", "routing", "specialist_execution", "validation", "deliverable", "next_action"],
    }


def _capability_plan(command: CommandSpec | None, raw_input: str, discovery: list[dict]) -> list[dict]:
    services = set()
    normalized = raw_input.casefold()
    if command and command.key == "deploy":
        services.update({"github", "railway"})
    if any(term in normalized for term in ("repo", "github", "branch", "commit", "code", "build", "test")):
        services.add("github")
    if any(term in normalized for term in ("model", "provider", "openrouter", "litellm")):
        services.update({"openrouter", "litellm"})
    if "hostinger" in normalized or "production" in normalized:
        services.add("hostinger")
    return [item for item in discovery if item["service"] in services]


def _blocker(
    code: str,
    capability: str,
    permission: str,
    service: str,
    action: str,
    resume: str,
) -> dict:
    return {
        "code": code,
        "required_capability": capability,
        "required_permission_or_credential": permission,
        "affected_service": service,
        "exact_human_action_required": action,
        "resume_command": resume,
    }


def _deployment_mission(db: Session) -> Mission | None:
    candidates = db.scalars(
        select(Mission)
        .join(CommandBrief, Mission.command_brief_id == CommandBrief.id)
        .where(
            Mission.status == MissionStatus.queued,
            CommandBrief.status.in_([BriefStatus.approved, BriefStatus.active]),
        )
        .order_by(Mission.priority.desc(), Mission.created_at)
    ).all()
    deploy_terms = ("deploy", "stage", "release", "publish")
    return next(
        (
            item
            for item in candidates
            if any(term in f"{item.action_key} {item.title}".casefold() for term in deploy_terms)
            and dependencies_satisfied(db, item)
        ),
        None,
    )


def _approve_reference(db: Session, reference_id: str | None, actor_role: str) -> tuple[list[str], list[dict], str]:
    if actor_role != "founder":
        return [], [
            _blocker(
                "approval_authority_required",
                "gateway.reference.approve",
                "Founder service identity",
                "cadre",
                "Resubmit the referenced approval through the Founder identity.",
                "+",
            )
        ], "Await authorized approval for the referenced Command Brief."
    if not reference_id:
        return [], [
            _blocker(
                "approval_reference_required",
                "gateway.reference.resolve",
                "Explicit Command Brief reference",
                "cadre",
                "Provide reference_id for the exact Command Brief being approved; no global approval is inferred.",
                "+ with reference_id",
            )
        ], "Provide the exact approval reference."
    brief = db.get(CommandBrief, reference_id)
    if brief is None:
        return [], [
            _blocker(
                "approval_reference_not_found",
                "gateway.reference.resolve",
                "Valid Command Brief identifier",
                "cadre",
                "Confirm the canonical Command Brief identifier and resubmit the approval.",
                "+ with valid reference_id",
            )
        ], "Resolve the canonical approval reference."
    if brief.status == BriefStatus.draft:
        brief.status = BriefStatus.approved
        return [f"Approved Command Brief {brief.id}"], [], "ADVANCE"
    if brief.status in {BriefStatus.approved, BriefStatus.active}:
        return [f"Command Brief {brief.id} was already approved"], [], "ADVANCE"
    return [], [
        _blocker(
            "approval_state_conflict",
            "gateway.reference.approve",
            "Command Brief in draft state",
            "cadre",
            f"Reconcile Command Brief {brief.id}, which is currently {brief.status.value}.",
            "STATUS",
        )
    ], "Reconcile the referenced Command Brief state."


def _render_items(values: Sequence[Any], *, empty: str = "None identified.") -> str:
    if not values:
        return f"- {empty}"
    return "\n".join(f"- {value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)}" for value in values)


def _execution_artifact(
    brief: CommandBrief,
    context: dict,
    specialists: dict,
    capability_plan: list[dict],
) -> dict:
    lead = specialists.get("lead_authority") or {"key": specialists["lead_specialist"], "name": specialists["lead_specialist"]}
    support = specialists.get("supporting_authorities", [])
    validator = specialists.get("validation_authority") or {
        "key": specialists["validation_specialist"],
        "name": specialists["validation_specialist"],
    }
    locked = list(context.get("locked_assets") or [])
    doctrine = [item.get("key") for item in context.get("doctrine", []) if item.get("key")]
    sources = list(dict.fromkeys([*brief.source_refs, *locked, *doctrine]))
    dependencies = [
        {
            "service": item["service"],
            "status": item["status"],
            "blockers": item.get("blockers", []),
        }
        for item in capability_plan
    ]
    role_lines = [f"Lead: {lead.get('name')} ({lead.get('key')}) — {lead.get('responsibility', 'owns the objective and integrated result')}."]
    role_lines.extend(
        f"Support: {item.get('name')} ({item.get('key')}) — {item.get('responsibility', 'supports the lead')}."
        for item in support
    )
    role_lines.append(
        f"Validator: {validator.get('name')} ({validator.get('key')}) — {validator.get('responsibility', 'independently validates acceptance')}."
    )
    note = "\n".join(
        [
            "# CADRE EXECUTION NOTE",
            "",
            f"Handoff ID: {brief.id}",
            f"Operating mode: {specialists.get('operating_mode', 'founder')}",
            "",
            "## Objective",
            brief.objective.strip(),
            "",
            "## Authority and specialist team",
            *role_lines,
            "",
            "## Governing decisions and locked constraints",
            _render_items(context.get("approved_decisions", [])),
            _render_items(brief.constraints),
            "",
            "## Source of truth",
            _render_items(sources, empty="Use the active project and doctrine registry recorded in this handoff."),
            "",
            "## Implementation requirements",
            "- Inspect the cited canonical state before modification.",
            "- Preserve every locked or unmentioned element.",
            "- Execute the objective through the named lead, support, and validation authorities.",
            "- Produce one integrated execution-ready result; do not return generic AI guidance.",
            "- Continue approved work until complete or a concrete authority or dependency gate is reached.",
            "",
            "## Technical specifications and dependencies",
            _render_items(dependencies, empty="No external service dependency was identified by capability discovery."),
            "",
            "## Security requirements",
            "- Use least privilege and server-side service identities.",
            "- Never place passwords, tokens, private keys, or credential values in prompts, artifacts, logs, source control, or public output.",
            "- Record only sanitized capability and validation metadata.",
            "",
            "## Preservation requirements",
            _render_items(locked, empty="Preserve the current canonical project state and rollback reference."),
            "",
            "## Commands and configuration",
            "- Use the canonical repository's existing commands and configuration for the assigned implementation.",
            "- Do not invent a path, environment value, credential, domain, or deployment target.",
            "- When an exact command is not supplied here, inspect the cited repository SOP before executing.",
            "",
            "## Validation and acceptance criteria",
            _render_items(brief.validation_criteria),
            "",
            "## Required outputs",
            _render_items(brief.expected_outputs),
            "",
            "## Reporting",
            "- Return changed artifacts/files, material evidence, validation results, exact accessible URLs when verified, remaining risks, and the next action.",
            "- Separate local validation, remote publication, deployment, authentication, and production readiness as distinct facts.",
            "- Provide both the actual artifact/file locator and this complete copy-ready execution note when a file is applicable.",
            "",
            "## Rollback and failure handling",
            f"- Preserve and use rollback reference: {context.get('rollback_reference') or 'resolve the canonical rollback reference before consequential mutation'}.",
            "- On failure: contain, preserve evidence, diagnose root cause, apply the smallest safe repair, rerun failed and regression checks, and report the exact blocker.",
        ]
    )
    return {
        "kind": "command_brief",
        "id": brief.id,
        "status": brief.status.value,
        "artifact": {
            "title": brief.title,
            "objective": brief.objective,
            "authority": brief.authority,
            "specialist_team": {
                "lead": lead,
                "support": support,
                "validator": validator,
            },
            "source_of_truth": sources,
            "locked_constraints": [*brief.constraints, *locked],
            "dependencies": dependencies,
            "required_outputs": list(brief.expected_outputs),
            "acceptance_criteria": list(brief.validation_criteria),
            "rollback_reference": context.get("rollback_reference"),
        },
        "copy_ready_note": note,
    }


def _signal_deliverables(db: Session, delivered_ids: set[str]) -> list[dict]:
    registered = db.scalars(
        select(MissionArtifact)
        .join(Mission, MissionArtifact.mission_id == Mission.id)
        .where(Mission.status == MissionStatus.verified)
        .order_by(MissionArtifact.created_at.desc())
        .limit(25)
    ).all()
    due = [item for item in registered if item.id not in delivered_ids]
    return [
        {
            "kind": "mission_artifact",
            "id": item.id,
            "mission_id": item.mission_id,
            "name": item.name,
            "source_locator": item.source_locator,
            "destination_locator": item.destination_locator,
            "archive_locator": item.archive_locator,
            "sha256": item.sha256,
            "state": item.state.value,
            "copy_ready_note": "\n".join(
                [
                    "# CADRE DELIVERY NOTE",
                    "",
                    f"Artifact: {item.name}",
                    f"Mission: {item.mission_id}",
                    f"Source: {item.source_locator}",
                    f"Destination: {item.destination_locator or 'not yet installed'}",
                    f"Archive: {item.archive_locator or 'not yet archived'}",
                    f"SHA-256: {item.sha256}",
                    f"State: {item.state.value}",
                    "",
                    "Dispatch the exact registered artifact. Verify its SHA-256 before use. Do not reconstruct, approximate, or substitute it.",
                ]
            ),
        }
        for item in due
    ]


def _draft_request(
    db: Session,
    context: dict,
    payload: GatewayInput,
    specialists: dict,
    capability_plan: list[dict],
) -> CommandBrief | None:
    project = context.get("active_project")
    if not project:
        return None
    title = " ".join(payload.raw_input.strip().split())[:120]
    if len(title) < 2:
        title = "Founder request"
    item = CommandBrief(
        project_id=project["id"],
        title=title,
        objective=payload.raw_input.strip(),
        authority="Founder request resolved through the LANSEIR Universal Prompt Gateway",
        current_state=json.dumps(
            {
                "milestone": context.get("current_milestone"),
                "next_executable_work": context.get("next_executable_work"),
            },
            default=str,
        ),
        constraints=[
            "respect locked source-of-truth assets",
            "preserve secrets and least privilege",
            "deliver copy-ready self-contained handoffs",
            "validate before completion",
        ],
        dependencies=[
            {"service": item["service"], "status": item["status"], "blockers": item.get("blockers", [])}
            for item in capability_plan
        ],
        expected_outputs=[
            "actual material deliverable or file locator",
            "complete copy-ready execution note",
            "validation evidence",
            "provenance receipt and explicit next action",
        ],
        validation_criteria=specialists["acceptance_criteria"],
        source_refs=specialists["canonical_sources_required"],
        specialist_roles=[
            specialists["lead_specialist"],
            *specialists["supporting_specialists"],
            specialists["validation_specialist"],
        ],
        status=BriefStatus.draft,
    )
    db.add(item)
    db.flush()
    return item


def _record_request(
    db: Session,
    settings: Settings,
    payload: GatewayInput,
    actor_role: str,
    command: CommandSpec | None,
    context: dict,
    specialists: dict,
    capability_plan: list[dict],
    status: GatewayStatus,
    actions_attempted: list[str],
    actions_completed: list[str],
    validation: list[dict],
    blockers: list[dict],
    artifacts: list[dict],
    next_action: str,
) -> GatewayRequest:
    digest = hashlib.sha256(payload.raw_input.encode("utf-8")).hexdigest()
    request_record = f"[content not retained; sha256:{digest}]"
    item = GatewayRequest(
        request_record=request_record,
        request_sha256=digest,
        command_key=command.key if command else "request",
        resolved_intent=command.intent if command else "Resolve a substantive request into a governed Command Brief.",
        interface=payload.interface,
        actor_role=actor_role,
        status=status,
        active_context=context,
        specialist_plan=specialists,
        capability_plan=capability_plan,
        actions_attempted=actions_attempted,
        actions_completed=actions_completed,
        validation=validation,
        blockers=blockers,
        artifacts=artifacts,
        commit_identifier=settings.release_id if settings.release_id != "development" else settings.last_validated_commit or None,
        next_executable_action=next_action,
    )
    db.add(item)
    db.flush()
    return item


def _update_state_from_request(
    state: ExecutionState,
    request: GatewayRequest,
    specialists: dict,
    actions_completed: list[str],
    blockers: list[dict],
    next_action: str,
    actor_role: str,
) -> None:
    payload = dict(state.payload)
    payload["assigned_agents"] = list(
        dict.fromkeys(
            [
                specialists["lead_specialist"],
                *specialists["supporting_specialists"],
                specialists["validation_specialist"],
            ]
        )
    )
    payload["next_executable_work"] = next_action or None
    existing_work = list(payload.get("work_in_progress", []))
    payload["work_in_progress"] = (existing_work + actions_completed)[-100:]
    existing_blockers = list(payload.get("blocked_work", []))
    payload["blocked_work"] = (existing_blockers + blockers)[-100:]
    payload["last_gateway_request_id"] = request.id
    if request.command_key == "signal":
        delivered = list(payload.get("delivered_artifact_ids", []))
        delivered.extend(
            item["id"]
            for item in request.artifacts
            if item.get("kind") == "mission_artifact" and item.get("id")
        )
        payload["delivered_artifact_ids"] = list(dict.fromkeys(delivered))[-500:]
        payload["last_signal_action"] = actions_completed[-1] if actions_completed else next_action
    if request.command_key == "deploy":
        deployment_state = dict(payload.get("deployment_state", {}))
        deployment_state["railway_staging"] = request.status.value
        payload["deployment_state"] = deployment_state
    if request.command_key == "approve_lock" and not blockers:
        approvals = list(payload.get("approved_decisions", []))
        approvals.append(
            {
                "decision": actions_completed[0] if actions_completed else "Referenced Command Brief approved",
                "authority": actor_role,
                "receipt": request.id,
            }
        )
        payload["approved_decisions"] = approvals[-100:]
    state.payload = payload
    state.revision += 1
    state.updated_by = actor_role


def resolve_gateway_request(
    db: Session,
    settings: Settings,
    payload: GatewayInput,
    *,
    actor_role: str,
    repository_root: Path | None = None,
) -> dict:
    command = resolve_command(payload.raw_input)
    context = build_context_packet(db, settings, project_id=payload.project_id, repository_root=repository_root)
    state = get_execution_state(db, settings)
    specialists = assemble_specialists(
        db,
        payload.raw_input,
        command,
        operating_mode=payload.operating_mode,
    )
    discovery = discover_capabilities(settings, repository_root)
    capability_plan = _capability_plan(command, payload.raw_input, discovery)
    actions_attempted: list[str] = []
    actions_completed: list[str] = []
    validation: list[dict] = []
    blockers: list[dict] = []
    artifacts: list[dict] = []
    next_action = ""
    status = GatewayStatus.resolved

    secret_detected = contains_potential_secret(payload.raw_input)
    if secret_detected:
        actions_attempted.append("screen_request_for_secrets")
        blockers.append(
            _blocker(
                "potential_secret_in_request",
                "gateway.request.secret_free",
                "Secret-free operational request",
                "cadre",
                "Remove credentials or secret values from the request, rotate any exposed credential, and resubmit only safe references.",
                "Resubmit the redacted command",
            )
        )
        validation.append({"check": "secret_screen", "passed": False, "detail": "Request content was not retained."})
        status = GatewayStatus.blocked
        next_action = "Remove and rotate the exposed secret, then resubmit a redacted request."
    elif command is None:
        actions_attempted.append("resolve_substantive_request")
        if not payload.execute:
            next_action = "Resubmit with execute=true to create the governed draft Command Brief."
        else:
            brief = _draft_request(db, context, payload, specialists, capability_plan)
            if brief is None:
                blockers.append(
                    _blocker(
                        "active_project_required",
                        "context.active_project",
                        "Canonical active project",
                        "cadre",
                        "Set or select the canonical active project, then resubmit the request.",
                        "STATUS",
                    )
                )
                status = GatewayStatus.blocked
                next_action = "Establish the canonical active project."
            else:
                actions_completed.append(f"Created governed draft Command Brief {brief.id}")
                artifacts.append(_execution_artifact(brief, context, specialists, capability_plan))
                validation.append({"check": "approval_gate", "passed": True, "detail": "Draft was not auto-approved."})
                status = GatewayStatus.awaiting_approval
                next_action = f"Approve reference {brief.id} with +, then issue ADVANCE."
    elif command.action == "report_status":
        actions_attempted.append("resolve_canonical_status")
        actions_completed.append("Returned canonical context packet")
        validation.append({"check": "state_loaded", "passed": True, "detail": f"Revision {context['state_revision']}"})
        status = GatewayStatus.completed
        next_action = (
            f"ADVANCE mission {context['next_executable_work']['id']}"
            if isinstance(context.get("next_executable_work"), dict)
            else "No approved executable mission is staged."
        )
    elif command.action == "approve_reference":
        actions_attempted.append("approve_referenced_command_brief")
        if payload.execute:
            completed, approval_blockers, next_action = _approve_reference(db, payload.reference_id, actor_role)
            actions_completed.extend(completed)
            blockers.extend(approval_blockers)
            status = GatewayStatus.blocked if blockers else GatewayStatus.completed
            validation.append({"check": "explicit_reference", "passed": not blockers, "detail": payload.reference_id or "missing"})
        else:
            next_action = "Resubmit with execute=true to apply the referenced approval."
    elif command.action == "dispatch_staged":
        actions_attempted.append("resolve_signal_sequence")
        delivered_ids = set(state.payload.get("delivered_artifact_ids", []))
        due = _signal_deliverables(db, delivered_ids)
        if due:
            actions_completed.append(f"Delivered {len(due)} due verified artifact(s)")
            artifacts.extend(due)
            validation.append({"check": "due_artifact_delivery", "passed": True, "detail": f"{len(due)} delivered"})
            status = GatewayStatus.completed
            next_action = "Use the exact delivered artifact and retain its checksum with the execution record."
        elif payload.execute:
            next_mission = dispatch_next(db)
            if next_mission is None:
                actions_completed.append("No approved executable work or due artifact was found")
                validation.append({"check": "canonical_state_resolved", "passed": True, "detail": f"Revision {context['state_revision']}"})
                status = GatewayStatus.completed
                next_action = "No approved executable mission or due artifact is staged."
            else:
                actions_completed.append(f"Dispatched mission {next_mission.id}")
                artifacts.append({"kind": "mission", "id": next_mission.id, "status": next_mission.status.value})
                validation.append({"check": "approval_and_dependencies", "passed": True, "detail": next_mission.command_brief_id})
                status = GatewayStatus.dispatched
                next_action = f"{next_mission.specialist_key} starts mission {next_mission.id} and registers its result for the following SIGNAL."
        else:
            next_action = "Resubmit SIGNAL with execute=true to advance approved work or deliver the due artifact."
    elif command.action == "deploy_staging":
        actions_attempted.extend(["discover_railway_capability", "resolve_deployment_ready_mission"])
        readiness = assess_production_readiness(state.payload.get("production_acceptance"))
        artifacts.append({"kind": "deployment_readiness", "assessment": readiness})
        validation.append(
            {
                "check": "production_readiness",
                "passed": readiness["ready"],
                "detail": readiness["status"],
                "missing": readiness["missing"],
            }
        )
        if not capability_ready(discovery, "railway", "staging.deploy"):
            blockers.append(
                _blocker(
                    "railway_staging_unavailable",
                    "railway.staging.deploy",
                    "Railway CLI, project identifier, and service credential",
                    "railway",
                    "Configure the Railway staging project and credential in the runtime; do not commit the credential.",
                    "DEPLOY",
                )
            )
            status = GatewayStatus.blocked
            next_action = "Configure Railway staging capability, then issue DEPLOY."
        else:
            mission = _deployment_mission(db)
            if mission is None:
                blockers.append(
                    _blocker(
                        "deployment_mission_required",
                        "mission.deploy_staging",
                        "Approved deployment-ready mission",
                        "cadre",
                        "Create and approve a mission with package, build, health, responsive, and rollback criteria.",
                        "DEPLOY",
                    )
                )
                status = GatewayStatus.blocked
                next_action = "Stage an approved deployment mission, then issue DEPLOY."
            elif payload.execute:
                dispatched = dispatch_mission(db, mission)
                actions_completed.append(f"Dispatched Railway staging mission {dispatched.id}")
                artifacts.append({"kind": "mission", "id": dispatched.id, "status": dispatched.status.value})
                status = GatewayStatus.dispatched
                next_action = f"Al executes mission {dispatched.id}; record deployment and HTTP verification evidence."
            else:
                next_action = f"Resubmit with execute=true to dispatch deployment mission {mission.id}."
    else:
        actions_attempted.append(command.action)
        if payload.execute:
            next_mission = dispatch_next(db)
            if next_mission is None:
                blockers.append(
                    _blocker(
                        "no_approved_executable_work",
                        "mission.dispatch",
                        "Approved queued mission with verified dependencies",
                        "cadre",
                        "Approve or stage the next bounded mission; existing locks and dependency gates will remain intact.",
                        "STATUS",
                    )
                )
                status = GatewayStatus.blocked
                next_action = "Stage an approved executable mission, then issue ADVANCE."
            else:
                actions_completed.append(f"Dispatched mission {next_mission.id}")
                artifacts.append({"kind": "mission", "id": next_mission.id, "status": next_mission.status.value})
                validation.append({"check": "approval_and_dependencies", "passed": True, "detail": next_mission.command_brief_id})
                status = GatewayStatus.dispatched
                next_action = f"{next_mission.specialist_key} starts mission {next_mission.id} and records material evidence."
        else:
            next_action = "Resubmit with execute=true to dispatch the canonical next mission."

    record = _record_request(
        db,
        settings,
        payload,
        actor_role,
        command,
        context,
        specialists,
        capability_plan,
        status,
        actions_attempted,
        actions_completed,
        validation,
        blockers,
        artifacts,
        next_action,
    )
    _update_state_from_request(state, record, specialists, actions_completed, blockers, next_action, actor_role)
    db.add(
        AuditEvent(
            event_type="gateway.request_resolved",
            resource_type="gateway_request",
            resource_id=record.id,
            request_id=record.id,
            metadata_json={
                "command": record.command_key,
                "status": record.status.value,
                "actor_role": actor_role,
                "request_sha256": record.request_sha256,
            },
        )
    )
    db.commit()
    db.refresh(record)
    response_request = (
        f"[potential secret redacted; sha256:{record.request_sha256}]"
        if secret_detected
        else payload.raw_input
    )
    return gateway_request_payload(record, request_text=response_request, state_revision=state.revision)


def gateway_request_payload(
    item: GatewayRequest,
    *,
    request_text: str | None = None,
    state_revision: int | None = None,
) -> dict:
    return {
        "id": item.id,
        "request": request_text if request_text is not None else item.request_record,
        "request_sha256": item.request_sha256,
        "command": item.command_key,
        "resolved_intent": item.resolved_intent,
        "active_context": item.active_context,
        "assigned_specialists": item.specialist_plan,
        "capability_routing": item.capability_plan,
        "actions_attempted": item.actions_attempted,
        "actions_completed": item.actions_completed,
        "validation": item.validation,
        "blockers": item.blockers,
        "artifacts": item.artifacts,
        "commit_identifier": item.commit_identifier,
        "deployment_identifier": item.deployment_identifier,
        "status": item.status.value,
        "state_revision": state_revision,
        "next_executable_action": item.next_executable_action,
        "created_at": item.created_at.isoformat(),
    }
