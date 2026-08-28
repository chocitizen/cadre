import hashlib

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import (
    ArtifactState,
    BriefStatus,
    CommandBrief,
    MissionStatus,
    Project,
    Specialist,
)
from app.services.mission_control import (
    add_evidence,
    create_mission,
    dispatch_next,
    fail_mission,
    porter_finalize,
    register_artifact,
    start_mission,
    submit_for_verification,
    verify_mission,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            Specialist(
                key="al",
                name="Al",
                responsibility="Recovery and durable improvement",
                permissions=["recovery"],
                routing_criteria=["failure"],
                validation_requirements=["verification_passed"],
            )
        )
        project = Project(slug="mission-engine", name="Mission Engine")
        session.add(project)
        session.flush()
        brief = CommandBrief(
            project_id=project.id,
            title="Deliver verified mission execution",
            objective="Prove evidence-gated execution and recovery",
            validation_criteria=["mission verified"],
            status=BriefStatus.approved,
        )
        session.add(brief)
        session.commit()
        yield session


def make_mission(db: Session, *, title: str = "Validate mission engine", max_retries: int = 1):
    brief = db.query(CommandBrief).one()
    return create_mission(
        db,
        command_brief_id=brief.id,
        title=title,
        action_key="validate_repository",
        specialist_key="al",
        priority=80,
        dependency_ids=[],
        input_payload={},
        expected_outputs=["test evidence"],
        validation_criteria=["verification passes"],
        max_retries=max_retries,
    )


def test_evidence_gates_completion_and_porter_lifecycle(db: Session):
    mission = make_mission(db)
    assert dispatch_next(db).id == mission.id
    mission = start_mission(db, mission.id)

    with pytest.raises(HTTPException, match="Status-only activity"):
        add_evidence(
            db,
            mission,
            created_by="al",
            kind="milestone_completed",
            summary="Still working",
            locator="",
            sha256=None,
            passed=True,
            metadata_json={},
        )

    digest = hashlib.sha256(b"mission artifact").hexdigest()
    artifact = register_artifact(
        db,
        mission.id,
        created_by="al",
        name="mission-report.json",
        source_locator="artifacts/mission-report.json",
        destination_locator="",
        sha256=digest,
        metadata_json={},
    )
    submit_for_verification(db, mission.id)
    add_evidence(
        db,
        mission,
        created_by="griot",
        kind="verification_passed",
        summary="Repository validation passed with zero failures",
        locator="validation/mission-engine.json",
        sha256=None,
        passed=True,
        metadata_json={"tests": 1},
    )
    verified, _ = verify_mission(db, mission.id)
    assert verified.status == MissionStatus.verified
    assert verified.command_brief.status == BriefStatus.completed

    finalized = porter_finalize(
        db,
        artifact.id,
        destination_locator="registry/mission-report.json",
        archive_locator="archive/mission-report.json",
        source_cleaned=True,
        verification_summary="Archived copy hash matches the registered artifact",
        created_by="porter",
    )
    assert finalized.state == ArtifactState.archived
    assert finalized.source_cleaned is True


def test_deterministic_failure_dispatches_recovery_before_retry(db: Session):
    mission = make_mission(db, title="Recover a deterministic failure")
    dispatch_next(db)
    start_mission(db, mission.id)
    original, recovery = fail_mission(
        db,
        mission.id,
        status=MissionStatus.failed,
        failure_class="deterministic",
        summary="Validation command failed with a reproducible configuration mismatch",
        root_cause="Repository policy still referenced the superseded remote",
        evidence_locator="validation/failure.json",
        created_by="al",
    )
    assert original.status == MissionStatus.recovering
    assert recovery is not None
    assert recovery.status == MissionStatus.dispatched
    assert recovery.recovery_for_id == original.id

    recovery = start_mission(db, recovery.id)
    add_evidence(
        db,
        recovery,
        created_by="al",
        kind="diagnosis",
        summary="The fixed repository policy caused the reproducible mismatch",
        locator="",
        sha256=None,
        passed=True,
        metadata_json={},
    )
    add_evidence(
        db,
        recovery,
        created_by="al",
        kind="repair_completed",
        summary="Repository policy was reconciled to the verified canonical remote",
        locator="ops/config/repository.json",
        sha256=None,
        passed=True,
        metadata_json={},
    )
    add_evidence(
        db,
        recovery,
        created_by="griot",
        kind="verification_passed",
        summary="Recovery validation passed and the original action is safe to resume",
        locator="validation/recovery.json",
        sha256=None,
        passed=True,
        metadata_json={},
    )
    submit_for_verification(db, recovery.id)
    verified_recovery, resumed = verify_mission(db, recovery.id)
    assert verified_recovery.status == MissionStatus.verified
    assert resumed is not None
    assert resumed.id == original.id
    assert resumed.status == MissionStatus.dispatched
    assert resumed.retry_count == 1
