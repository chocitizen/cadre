from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.models.entities import BriefStatus, CommandBrief, ExecutionState, Mission, MissionArtifact, MissionStatus, Project, User
from app.schemas.gateway import GatewayInput
from app.services.deployment import PRODUCTION_READINESS_GATES, assess_production_readiness
from app.services.gateway import resolve_gateway_request
from app.services.identity import verify_password
from app.services.owner_provisioning import provision_owner
from app.services.seed import seed_doctrine, seed_product


def make_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_doctrine(db)
        seed_product(db)
    return engine


def settings(**changes):
    base = Settings(
        database_url="sqlite:///:memory:",
        api_tokens_json=json.dumps({"mission_control": "a" * 32}),
        railway_project_id="",
        railway_token="",
        ai_provider="local",
        admin_emails="owner@example.com",
    )
    return base.model_copy(update=changes)


def test_typed_and_voice_execution_generate_equal_authority_and_complete_copy_ready_handoffs():
    engine = make_engine()
    with Session(engine) as db:
        typed = resolve_gateway_request(
            db,
            settings(),
            GatewayInput(raw_input="Build and validate the protected client release", interface="typed"),
            actor_role="founder",
        )
        voice = resolve_gateway_request(
            db,
            settings(),
            GatewayInput(raw_input="Build and validate the protected client release", interface="voice"),
            actor_role="founder",
        )

    for result in (typed, voice):
        assert result["status"] == "awaiting_approval"
        assert result["assigned_specialists"]["lead_authority"]["name"] == "Al"
        assert result["assigned_specialists"]["validation_authority"]["name"] in {"Griot", "Invictus"}
        artifact = result["artifacts"][0]
        assert artifact["artifact"]["specialist_team"]["lead"]["standards"]
        note = artifact["copy_ready_note"]
        assert note.startswith("# CADRE EXECUTION NOTE")
        for heading in (
            "## Objective",
            "## Authority and specialist team",
            "## Governing decisions and locked constraints",
            "## Source of truth",
            "## Implementation requirements",
            "## Technical specifications and dependencies",
            "## Security requirements",
            "## Preservation requirements",
            "## Commands and configuration",
            "## Validation and acceptance criteria",
            "## Required outputs",
            "## Reporting",
            "## Rollback and failure handling",
        ):
            assert heading in note
        assert "What would you like" not in note
        assert "I will now" not in note

    assert typed["assigned_specialists"]["lead_specialist"] == voice["assigned_specialists"]["lead_specialist"]
    assert typed["artifacts"][0]["artifact"]["acceptance_criteria"] == voice["artifacts"][0]["artifact"]["acceptance_criteria"]


def test_client_mode_inherits_founder_quality_and_adds_client_authority():
    engine = make_engine()
    with Session(engine) as db:
        result = resolve_gateway_request(
            db,
            settings(),
            GatewayInput(
                raw_input="Implement and validate the client onboarding workflow",
                interface="mobile",
                operating_mode="client",
            ),
            actor_role="mission_control",
        )
    plan = result["assigned_specialists"]
    assert plan["operating_mode"] == "client"
    assert plan["experience_sequence"] == ["intent", "routing", "specialist_execution", "validation", "deliverable", "next_action"]
    assert any(item["key"] == "liv" for item in plan["supporting_authorities"])
    assert result["artifacts"][0]["copy_ready_note"].startswith("# CADRE EXECUTION NOTE")


def test_first_signal_advances_and_following_signal_dual_delivers_verified_file():
    engine = make_engine()
    with Session(engine) as db:
        project = db.query(Project).filter_by(slug="lanseir-platform").one()
        brief = CommandBrief(
            project_id=project.id,
            title="Deliver the governed file",
            objective="Create and deliver the governed file",
            validation_criteria=["artifact verified"],
            status=BriefStatus.approved,
        )
        db.add(brief)
        db.flush()
        mission = Mission(
            command_brief_id=brief.id,
            title="Create governed file",
            action_key="create_governed_file",
            specialist_key="al",
            validation_criteria=["artifact verified"],
        )
        db.add(mission)
        db.commit()

        first = resolve_gateway_request(db, settings(), GatewayInput(raw_input="SIGNAL"), actor_role="founder")
        assert first["status"] == "dispatched"
        assert first["artifacts"] == [{"kind": "mission", "id": mission.id, "status": "dispatched"}]

        mission.status = MissionStatus.verified
        artifact = MissionArtifact(
            mission_id=mission.id,
            name="governed-output.md",
            source_locator="artifacts/governed-output.md",
            destination_locator="deliverables/governed-output.md",
            sha256=hashlib.sha256(b"governed output").hexdigest(),
        )
        db.add(artifact)
        db.commit()

        second = resolve_gateway_request(db, settings(), GatewayInput(raw_input="SIGNAL"), actor_role="founder")
        assert second["status"] == "completed"
        delivered = second["artifacts"][0]
        assert delivered["kind"] == "mission_artifact"
        assert delivered["source_locator"] == "artifacts/governed-output.md"
        assert delivered["sha256"] == artifact.sha256
        assert delivered["copy_ready_note"].startswith("# CADRE DELIVERY NOTE")
        state = db.get(ExecutionState, "canonical")
        assert artifact.id in state.payload["delivered_artifact_ids"]


def test_signal_with_no_work_returns_concise_current_state_without_false_blocker():
    engine = make_engine()
    with Session(engine) as db:
        result = resolve_gateway_request(db, settings(), GatewayInput(raw_input="SIGNAL"), actor_role="founder")
    assert result["status"] == "completed"
    assert result["blockers"] == []
    assert result["actions_completed"] == ["No approved executable work or due artifact was found"]


def test_deployment_ready_is_fail_closed_until_every_production_gate_passes():
    partial = assess_production_readiness({"production_build_successful": True, "rollback_available": True})
    assert partial["status"] == "NOT_READY"
    assert "owner_account_provisioned" in partial["missing"]
    assert "production_authentication_verified" in partial["missing"]
    assert "exact_login_url_captured" in partial["missing"]

    evidence = {key: True for key in PRODUCTION_READINESS_GATES}
    evidence.update({"live_login_url": "https://cadre.example.com/#access", "owner_email": "owner@example.com"})
    complete = assess_production_readiness(evidence)
    assert complete == {
        "status": "READY",
        "ready": True,
        "gates": {**{key: True for key in PRODUCTION_READINESS_GATES}, "exact_login_url_captured": True, "owner_identity_recorded": True},
        "missing": [],
        "live_login_url": "https://cadre.example.com/#access",
        "owner_email": "owner@example.com",
    }


def test_deploy_response_cannot_report_ready_from_build_or_health_only():
    engine = make_engine()
    with Session(engine) as db:
        state = db.get(ExecutionState, "canonical")
        state.payload = {**state.payload, "production_acceptance": {"production_build_successful": True, "required_services_operational": True}}
        db.commit()
        result = resolve_gateway_request(db, settings(), GatewayInput(raw_input="DEPLOY"), actor_role="founder")
    assessment = next(item["assessment"] for item in result["artifacts"] if item["kind"] == "deployment_readiness")
    assert result["status"] == "blocked"
    assert assessment["status"] == "NOT_READY"
    assert assessment["ready"] is False


def test_owner_provisioning_is_allowlisted_audited_and_never_echoes_password():
    engine = make_engine()
    password = "MajesticOwnerPass2026"
    with Session(engine) as db:
        receipt = provision_owner(db, settings(), email="owner@example.com", password=password)
        owner = db.query(User).filter_by(email="owner@example.com").one()
        assert owner.role == "admin"
        assert owner.email_verified_at is not None
        assert verify_password(password, owner.password_hash)
        assert password not in json.dumps(receipt)
        assert receipt["credential_exposed"] is False

        second = provision_owner(db, settings(), email="owner@example.com")
        assert second["created"] is False
        assert second["password_changed"] is False
