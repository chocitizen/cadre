from __future__ import annotations

import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.models.entities import BriefStatus, CommandBrief, ExecutionState, GatewayRequest, Mission, Project
from app.schemas.gateway import GatewayInput
from app.services.capabilities import discover_capabilities
from app.services.command_registry import resolve_command
from app.services.gateway import (
    build_context_packet,
    patch_execution_state,
    resolve_gateway_request,
)
from app.services.seed import seed_doctrine, seed_product


@pytest.fixture
def engine():
    value = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(value)
    with Session(value) as db:
        seed_doctrine(db)
        seed_product(db)
    return value


@pytest.fixture
def settings():
    return Settings(
        database_url="sqlite:///:memory:",
        api_tokens_json=json.dumps({"mission_control": "a" * 32}),
        github_repository="",
        github_token="",
        railway_project_id="",
        railway_token="",
        ai_provider="local",
        ai_api_key="",
        hostinger_operations_enabled=False,
        hostinger_ssh_host="",
    )


def test_short_commands_have_durable_exact_semantics():
    expected = {
        "Signal": "signal",
        "Now": "now",
        "Go": "now",
        "Advance": "advance",
        "Act": "advance",
        "Actively advance": "actively_advance",
        "Deploy": "deploy",
        "Status": "status",
        "+": "approve_lock",
        "You know what to do": "resolve_continue",
    }
    for raw_input, key in expected.items():
        resolved = resolve_command(raw_input)
        assert resolved is not None
        assert resolved.key == key
    assert resolve_command("Please give me deployment status") is None


def test_status_resolves_context_and_persists_a_privacy_aware_receipt(engine, settings):
    with Session(engine) as db:
        result = resolve_gateway_request(
            db,
            settings,
            GatewayInput(raw_input="Status"),
            actor_role="mission_control",
        )
        request_id = result["id"]
        assert result["status"] == "completed"
        assert result["command"] == "status"
        assert result["active_context"]["active_project"]["slug"] == "lanseir-platform"
        assert "What would you like" not in json.dumps(result)

    with Session(engine) as fresh_session:
        receipt = fresh_session.get(GatewayRequest, request_id)
        state = fresh_session.get(ExecutionState, "canonical")
        assert receipt is not None
        assert receipt.request_record.startswith("[content not retained; sha256:")
        assert state is not None
        assert state.payload["last_gateway_request_id"] == request_id
        assert state.revision == 2


def test_substantive_request_is_routed_drafted_approved_and_dispatched(engine, settings):
    with Session(engine) as db:
        drafted = resolve_gateway_request(
            db,
            settings,
            GatewayInput(raw_input="Build and validate the repository release gateway"),
            actor_role="al",
        )
        assert drafted["status"] == "awaiting_approval"
        assert drafted["assigned_specialists"]["lead_specialist"] == "al"
        brief_id = drafted["artifacts"][0]["id"]
        brief = db.get(CommandBrief, brief_id)
        assert brief is not None
        assert brief.status == BriefStatus.draft

        denied = resolve_gateway_request(
            db,
            settings,
            GatewayInput(raw_input="+", reference_id=brief_id),
            actor_role="al",
        )
        assert denied["status"] == "blocked"
        assert denied["blockers"][0]["code"] == "approval_authority_required"

        approved = resolve_gateway_request(
            db,
            settings,
            GatewayInput(raw_input="+", reference_id=brief_id),
            actor_role="founder",
        )
        assert approved["status"] == "completed"
        db.refresh(brief)
        assert brief.status == BriefStatus.approved

        mission = Mission(
            command_brief_id=brief.id,
            title="Implement the gateway",
            action_key="implement_gateway",
            specialist_key="al",
            validation_criteria=["tests pass"],
        )
        db.add(mission)
        db.commit()

        advanced = resolve_gateway_request(
            db,
            settings,
            GatewayInput(raw_input="Actively advance"),
            actor_role="founder",
        )
        assert advanced["status"] == "dispatched"
        db.refresh(mission)
        assert mission.status.value == "dispatched"


def test_deploy_returns_exact_railway_blocker_without_claiming_capability(engine, settings):
    with Session(engine) as db:
        result = resolve_gateway_request(
            db,
            settings,
            GatewayInput(raw_input="Deploy"),
            actor_role="founder",
        )
        assert result["status"] == "blocked"
        blocker = result["blockers"][0]
        assert blocker == {
            "code": "railway_staging_unavailable",
            "required_capability": "railway.staging.deploy",
            "required_permission_or_credential": "Railway CLI, project identifier, and service credential",
            "affected_service": "railway",
            "exact_human_action_required": "Configure the Railway staging project and credential in the runtime; do not commit the credential.",
            "resume_command": "DEPLOY",
        }


def test_context_respects_locked_sources_and_state_revision(engine, settings):
    with Session(engine) as db:
        context = build_context_packet(db, settings)
        assert "source_of_truth_registry.json" in context["locked_assets"]
        state = db.get(ExecutionState, "canonical")
        assert state is not None
        with pytest.raises(HTTPException, match="Founder authority"):
            patch_execution_state(
                db,
                settings,
                expected_revision=state.revision,
                changes={"locked_assets": []},
                actor_role="al",
            )
        db.rollback()
        state = db.get(ExecutionState, "canonical")
        assert state is not None
        updated = patch_execution_state(
            db,
            settings,
            expected_revision=state.revision,
            changes={"current_objective": "Validate context portability"},
            actor_role="al",
        )
        assert updated.revision == 2
        assert updated.payload["current_objective"] == "Validate context portability"


def test_service_discovery_never_echoes_credentials(settings):
    secret = "super-secret-token-value-that-must-not-leak"
    configured = settings.model_copy(
        update={
            "github_repository": "owner/repository",
            "github_token": secret,
            "railway_project_id": "project-id",
            "railway_token": secret,
            "ai_provider": "openrouter",
            "ai_api_key": secret,
        }
    )
    payload = discover_capabilities(configured)
    rendered = json.dumps(payload)
    assert secret not in rendered
    assert {item["service"] for item in payload} == {"github", "railway", "openrouter", "litellm", "hostinger"}


def test_secret_like_request_is_blocked_redacted_and_not_promoted(engine, settings):
    secret_label = "api" + "_key"
    exposed = f"{secret_label}={'z' * 32}"
    with Session(engine) as db:
        before = db.query(CommandBrief).count()
        result = resolve_gateway_request(
            db,
            settings,
            GatewayInput(raw_input=f"Deploy with {exposed}"),
            actor_role="founder",
        )
        assert result["status"] == "blocked"
        assert result["blockers"][0]["code"] == "potential_secret_in_request"
        assert exposed not in json.dumps(result)
        assert db.query(CommandBrief).count() == before
        receipt = db.get(GatewayRequest, result["id"])
        assert receipt is not None
        assert exposed not in receipt.request_record
