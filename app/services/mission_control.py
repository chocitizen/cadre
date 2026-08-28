from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AgentRun,
    ArtifactState,
    BriefStatus,
    CommandBrief,
    Mission,
    MissionArtifact,
    MissionEvidence,
    MissionStatus,
    RunStatus,
    Specialist,
)


FAILURE_STATES = frozenset(
    {
        MissionStatus.failed,
        MissionStatus.blocked,
        MissionStatus.stalled,
        MissionStatus.verification_failed,
    }
)
TERMINAL_STATES = frozenset({MissionStatus.verified, MissionStatus.cancelled})
AUTO_RECOVERY_CLASSES = frozenset({"deterministic"})
EVIDENCE_KINDS_REQUIRING_LOCATOR = frozenset(
    {
        "artifact_created",
        "code_committed",
        "test_passed",
        "deployment_completed",
        "verification_passed",
        "archive_completed",
    }
)
STATUS_ONLY_MESSAGES = frozenset(
    {
        "working",
        "active",
        "still working",
        "processing",
        "heartbeat received",
        "agent alive",
        "continuing",
        "progress underway",
    }
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _not_found(resource: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} not found")


def _normalized_summary(summary: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", summary.casefold()).split())


def _assert_material_evidence(kind: str, summary: str, locator: str) -> None:
    if _normalized_summary(summary) in STATUS_ONLY_MESSAGES:
        raise HTTPException(status_code=422, detail="Status-only activity is not mission progress")
    if kind in EVIDENCE_KINDS_REQUIRING_LOCATOR and not locator.strip():
        raise HTTPException(status_code=422, detail=f"{kind} evidence requires a durable locator")


def create_mission(db: Session, **values) -> Mission:
    brief = db.get(CommandBrief, values["command_brief_id"])
    if brief is None:
        raise _not_found("Command brief")
    if brief.status not in {BriefStatus.approved, BriefStatus.active}:
        raise HTTPException(status_code=409, detail="Only approved objectives may receive executable missions")

    dependencies = values.get("dependency_ids", [])
    if len(set(dependencies)) != len(dependencies):
        raise HTTPException(status_code=422, detail="Mission dependencies must be unique")
    if dependencies:
        dependency_rows = db.scalars(select(Mission).where(Mission.id.in_(dependencies))).all()
        if len(dependency_rows) != len(dependencies) or any(item.command_brief_id != brief.id for item in dependency_rows):
            raise HTTPException(status_code=422, detail="Dependencies must reference missions in the same command brief")

    if db.scalar(select(Specialist).where(Specialist.key == values["specialist_key"], Specialist.is_active.is_(True))) is None:
        raise HTTPException(status_code=422, detail="Mission specialist is unavailable")

    item = Mission(**values)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def dependencies_satisfied(db: Session, mission: Mission) -> bool:
    dependency_ids = list(mission.dependency_ids or [])
    if not dependency_ids:
        return True
    dependencies = db.scalars(select(Mission).where(Mission.id.in_(dependency_ids))).all()
    return len(dependencies) == len(dependency_ids) and all(item.status == MissionStatus.verified for item in dependencies)


def _dispatch(db: Session, item: Mission) -> Mission:
    item.status = MissionStatus.dispatched
    item.command_brief.status = BriefStatus.active
    db.add(
        AgentRun(
            specialist_key=item.specialist_key,
            task_kind=item.action_key,
            status=RunStatus.queued,
            result_summary="",
            usage={"mission_id": item.id, "command_brief_id": item.command_brief_id},
        )
    )
    db.commit()
    db.refresh(item)
    return item


def dispatch_next(db: Session) -> Mission | None:
    candidates = db.scalars(
        select(Mission)
        .join(CommandBrief, Mission.command_brief_id == CommandBrief.id)
        .where(
            Mission.status == MissionStatus.queued,
            CommandBrief.status.in_([BriefStatus.approved, BriefStatus.active]),
        )
        .order_by(Mission.priority.desc(), Mission.created_at, Mission.id)
    ).all()
    item = next((candidate for candidate in candidates if dependencies_satisfied(db, candidate)), None)
    if item is None:
        return None
    return _dispatch(db, item)


def start_mission(db: Session, mission_id: str) -> Mission:
    item = db.get(Mission, mission_id)
    if item is None:
        raise _not_found("Mission")
    if item.status != MissionStatus.dispatched:
        raise HTTPException(status_code=409, detail="Only dispatched missions may start")
    item.status = MissionStatus.running
    item.started_at = utcnow()
    _update_agent_run(db, item, "running")
    db.commit()
    db.refresh(item)
    return item


def add_evidence(db: Session, mission: Mission, *, created_by: str, **values) -> MissionEvidence:
    _assert_material_evidence(values["kind"], values["summary"], values.get("locator", ""))
    evidence = MissionEvidence(mission_id=mission.id, created_by=created_by, **values)
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def submit_for_verification(db: Session, mission_id: str) -> Mission:
    item = db.get(Mission, mission_id)
    if item is None:
        raise _not_found("Mission")
    if item.status != MissionStatus.running:
        raise HTTPException(status_code=409, detail="Only running missions may enter verification")
    evidence = db.scalars(select(MissionEvidence).where(MissionEvidence.mission_id == item.id, MissionEvidence.passed.is_(True))).all()
    material = [record for record in evidence if record.kind not in {"failure_captured", "diagnosis"}]
    if not material:
        raise HTTPException(status_code=409, detail="Mission progress requires material evidence before verification")
    if item.recovery_for_id:
        kinds = {record.kind for record in evidence if record.passed}
        if not {"diagnosis", "repair_completed"}.issubset(kinds):
            raise HTTPException(status_code=409, detail="Recovery requires diagnosis and repair evidence before verification")
    item.status = MissionStatus.verification_pending
    db.commit()
    db.refresh(item)
    return item


def _update_agent_run(db: Session, mission: Mission, status: str, summary: str = "") -> None:
    runs = db.scalars(select(AgentRun).order_by(AgentRun.created_at.desc())).all()
    run = next((candidate for candidate in runs if candidate.usage.get("mission_id") == mission.id), None)
    if run is not None:
        run.status = RunStatus(status)
        run.result_summary = summary
        if status in {"completed", "failed", "blocked"}:
            run.completed_at = utcnow()


def _complete_brief_if_verified(db: Session, brief: CommandBrief) -> None:
    missions = db.scalars(select(Mission).where(Mission.command_brief_id == brief.id)).all()
    if missions and all(item.status == MissionStatus.verified for item in missions):
        brief.status = BriefStatus.completed


def verify_mission(db: Session, mission_id: str) -> tuple[Mission, Mission | None]:
    item = db.get(Mission, mission_id)
    if item is None:
        raise _not_found("Mission")
    if item.status != MissionStatus.verification_pending:
        raise HTTPException(status_code=409, detail="Mission is not awaiting verification")
    proof = db.scalar(
        select(MissionEvidence).where(
            MissionEvidence.mission_id == item.id,
            MissionEvidence.kind == "verification_passed",
            MissionEvidence.passed.is_(True),
        )
    )
    if proof is None:
        raise HTTPException(status_code=409, detail="Verification cannot pass without verification evidence")

    item.status = MissionStatus.verified
    item.completed_at = utcnow()
    item.verified_at = item.completed_at
    _update_agent_run(db, item, "completed", "Verified mission evidence recorded")

    resumed = None
    if item.recovery_for_id:
        original = db.get(Mission, item.recovery_for_id)
        if original is not None:
            if original.retry_count >= original.max_retries:
                original.status = MissionStatus.blocked
            else:
                original.retry_count += 1
                original.status = MissionStatus.queued
                original.started_at = None
                original.completed_at = None
                original.verified_at = None
                resumed = original

    _complete_brief_if_verified(db, item.command_brief)
    db.commit()
    db.refresh(item)
    next_mission = dispatch_next(db)
    return item, resumed or next_mission


def _open_recovery(db: Session, original: Mission) -> Mission | None:
    candidates = db.scalars(select(Mission).where(Mission.recovery_for_id == original.id)).all()
    return next((item for item in candidates if item.status not in TERMINAL_STATES), None)


def create_recovery(db: Session, original: Mission) -> Mission:
    existing = _open_recovery(db, original)
    if existing is not None:
        return _dispatch(db, existing) if existing.status == MissionStatus.queued else existing
    if original.retry_count >= original.max_retries:
        raise HTTPException(status_code=409, detail="Mission recovery retry limit is exhausted")
    recovery = Mission(
        command_brief_id=original.command_brief_id,
        recovery_for_id=original.id,
        title=f"Recover: {original.title}",
        action_key="recover_failure",
        specialist_key="al",
        priority=100,
        input_payload={
            "original_mission_id": original.id,
            "failure_class": original.failure_class,
            "root_cause": original.root_cause,
        },
        expected_outputs=["diagnosis", "repair", "verification", "original mission resumed"],
        validation_criteria=["root cause recorded", "repair evidence recorded", "verification passed"],
        max_retries=0,
    )
    original.status = MissionStatus.recovering
    db.add(recovery)
    db.commit()
    db.refresh(recovery)
    return _dispatch(db, recovery)


def fail_mission(
    db: Session,
    mission_id: str,
    *,
    status: MissionStatus,
    failure_class: str,
    summary: str,
    root_cause: str,
    evidence_locator: str,
    created_by: str,
) -> tuple[Mission, Mission | None]:
    item = db.get(Mission, mission_id)
    if item is None:
        raise _not_found("Mission")
    if item.status not in {MissionStatus.dispatched, MissionStatus.running, MissionStatus.verification_pending}:
        raise HTTPException(status_code=409, detail="Mission cannot fail from its current state")
    if status not in FAILURE_STATES:
        raise HTTPException(status_code=422, detail="Failure status must expose FIX")
    item.status = status
    item.failure_class = failure_class
    item.root_cause = root_cause.strip()
    item.completed_at = utcnow()
    db.add(
        MissionEvidence(
            mission_id=item.id,
            kind="failure_captured",
            summary=summary,
            locator=evidence_locator,
            passed=False,
            metadata_json={"failure_class": failure_class},
            created_by=created_by,
        )
    )
    _update_agent_run(db, item, "blocked" if status == MissionStatus.blocked else "failed", summary)
    db.commit()
    db.refresh(item)
    recovery = create_recovery(db, item) if failure_class in AUTO_RECOVERY_CLASSES else None
    return item, recovery


def fix_mission(db: Session, mission_id: str) -> Mission:
    item = db.get(Mission, mission_id)
    if item is None:
        raise _not_found("Mission")
    if item.status not in FAILURE_STATES and item.status != MissionStatus.recovering:
        raise HTTPException(status_code=409, detail="FIX is available only for failed, blocked, stalled, or verification-failed missions")
    return create_recovery(db, item)


def register_artifact(db: Session, mission_id: str, *, created_by: str, **values) -> MissionArtifact:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise _not_found("Mission")
    if mission.status not in {MissionStatus.running, MissionStatus.verification_pending}:
        raise HTTPException(status_code=409, detail="Artifacts may be registered only during active mission execution")
    duplicate = db.scalar(
        select(MissionArtifact).where(
            MissionArtifact.mission_id == mission.id,
            MissionArtifact.sha256 == values["sha256"],
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Artifact hash is already registered for this mission")
    artifact = MissionArtifact(mission_id=mission.id, **values)
    db.add(artifact)
    db.flush()
    db.add(
        MissionEvidence(
            mission_id=mission.id,
            kind="artifact_created",
            summary=f"Artifact registered: {artifact.name}",
            locator=artifact.source_locator,
            sha256=artifact.sha256,
            passed=True,
            metadata_json={"artifact_id": artifact.id},
            created_by=created_by,
        )
    )
    db.commit()
    db.refresh(artifact)
    return artifact


def porter_finalize(
    db: Session,
    artifact_id: str,
    *,
    destination_locator: str,
    archive_locator: str,
    source_cleaned: bool,
    verification_summary: str,
    created_by: str,
) -> MissionArtifact:
    artifact = db.get(MissionArtifact, artifact_id)
    if artifact is None:
        raise _not_found("Artifact")
    if artifact.mission.status != MissionStatus.verified:
        raise HTTPException(status_code=409, detail="Porter may finalize only verified mission artifacts")
    if artifact.state == ArtifactState.archived:
        return artifact
    if source_cleaned and artifact.source_locator in {destination_locator, archive_locator}:
        raise HTTPException(status_code=422, detail="Porter cannot clean the only registered artifact copy")
    _assert_material_evidence("archive_completed", verification_summary, archive_locator)
    artifact.destination_locator = destination_locator
    artifact.archive_locator = archive_locator
    artifact.source_cleaned = source_cleaned
    artifact.state = ArtifactState.archived
    db.add_all(
        [
            MissionEvidence(
                mission_id=artifact.mission_id,
                kind="archive_completed",
                summary=verification_summary,
                locator=archive_locator,
                sha256=artifact.sha256,
                passed=True,
                metadata_json={"artifact_id": artifact.id, "destination": destination_locator},
                created_by=created_by,
            ),
            MissionEvidence(
                mission_id=artifact.mission_id,
                kind="cleanup_completed",
                summary=("Verified source duplicate removed" if source_cleaned else "Source retained as recovery material"),
                locator=artifact.source_locator,
                sha256=artifact.sha256,
                passed=True,
                metadata_json={"artifact_id": artifact.id, "source_cleaned": source_cleaned},
                created_by=created_by,
            ),
        ]
    )
    db.commit()
    db.refresh(artifact)
    return artifact


def mission_snapshot(db: Session) -> dict:
    briefs = db.scalars(select(CommandBrief).order_by(CommandBrief.created_at.desc())).all()
    missions = db.scalars(select(Mission).order_by(Mission.priority.desc(), Mission.created_at)).all()
    evidence = db.scalars(select(MissionEvidence).order_by(MissionEvidence.created_at.desc()).limit(100)).all()
    artifacts = db.scalars(select(MissionArtifact).order_by(MissionArtifact.created_at.desc()).limit(100)).all()
    return {
        "briefs": briefs,
        "missions": missions,
        "evidence": evidence,
        "artifacts": artifacts,
        "next_executable_mission_id": next((item.id for item in missions if item.status == MissionStatus.queued and dependencies_satisfied(db, item)), None),
    }
