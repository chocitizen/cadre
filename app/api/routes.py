import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import get_settings
from app.core.security import (
    ApiIdentity,
    require_admin_promotion,
    require_doctrine_read,
    require_mission_read,
    require_mission_verify,
    require_mission_write,
    require_operations_read,
    require_porter_write,
    require_registry_read,
    require_write,
)
from app.models.entities import (
    AuditEvent,
    Book,
    BriefStatus,
    CanonicalContentSource,
    CommandBrief,
    ContentSourceStatus,
    DoctrineEntry,
    Mission,
    Project,
    User,
    utcnow,
)
from app.schemas.entities import (
    ArtifactCreate,
    ArtifactOut,
    BriefCreate,
    BriefOut,
    ContentSourceCreate,
    DoctrineCreate,
    DoctrineOut,
    EvidenceCreate,
    EvidenceOut,
    MissionCreate,
    MissionFailure,
    MissionOut,
    PorterFinalize,
    ProjectCreate,
    ProjectOut,
)
from app.services.mission_control import (
    add_evidence,
    create_mission,
    dispatch_next,
    fail_mission,
    fix_mission,
    mission_snapshot,
    porter_finalize,
    register_artifact,
    start_mission,
    submit_for_verification,
    verify_mission,
)

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "system": "CADRE",
        "milestone": "M4",
        "version": "0.5.0",
        "release": settings.release_id,
    }


@router.get("/operations/state")
def operations_state(_: ApiIdentity = Depends(require_operations_read)) -> dict:
    """Return the sanitized, read-only Mission Control state snapshot.

    The production reverse proxy does not publish this route. It is available
    only on the loopback/internal API boundary for Mission Control.
    """
    state_path = Path(settings.operations_state_path)
    if not state_path.is_file():
        return {
            "system": "DEGRADED",
            "deployment": "QUEUED",
            "current_release": None,
            "agents": [],
            "detail": "Operations state has not been initialized on this host.",
        }
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Operations state is unavailable")
    allowed = {
        "system",
        "deployment",
        "current_release",
        "last_known_good_release",
        "last_operation",
        "updated_at",
        "agents",
    }
    return {key: payload[key] for key in allowed if key in payload}


def _mission_payload(item: Mission) -> dict:
    return {
        "id": item.id,
        "command_brief_id": item.command_brief_id,
        "recovery_for_id": item.recovery_for_id,
        "title": item.title,
        "action_key": item.action_key,
        "specialist_key": item.specialist_key,
        "status": item.status.value,
        "priority": item.priority,
        "dependency_ids": item.dependency_ids,
        "input_payload": item.input_payload,
        "expected_outputs": item.expected_outputs,
        "validation_criteria": item.validation_criteria,
        "failure_class": item.failure_class,
        "root_cause": item.root_cause,
        "retry_count": item.retry_count,
        "max_retries": item.max_retries,
        "fix_available": item.status.value in {"failed", "blocked", "stalled", "verification_failed"},
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "started_at": item.started_at,
        "completed_at": item.completed_at,
        "verified_at": item.verified_at,
    }


@router.get("/mission-control")
def get_mission_control(_: ApiIdentity = Depends(require_mission_read), db: Session = Depends(get_db)) -> dict:
    snapshot = mission_snapshot(db)
    return {
        "briefs": [BriefOut.model_validate(item).model_dump(mode="json") for item in snapshot["briefs"]],
        "missions": [_mission_payload(item) for item in snapshot["missions"]],
        "evidence": [
            {
                "id": item.id,
                "mission_id": item.mission_id,
                "kind": item.kind,
                "summary": item.summary,
                "locator": item.locator,
                "sha256": item.sha256,
                "passed": item.passed,
                "metadata": item.metadata_json,
                "created_by": item.created_by,
                "created_at": item.created_at,
            }
            for item in snapshot["evidence"]
        ],
        "artifacts": [ArtifactOut.model_validate(item).model_dump(mode="json") for item in snapshot["artifacts"]],
        "next_executable_mission_id": snapshot["next_executable_mission_id"],
    }


@router.post("/mission-control/missions", response_model=MissionOut, status_code=status.HTTP_201_CREATED)
def create_mission_record(
    payload: MissionCreate,
    _: ApiIdentity = Depends(require_mission_write),
    db: Session = Depends(get_db),
):
    return create_mission(db, **payload.model_dump())


@router.post("/mission-control/dispatch")
def dispatch_mission(_: ApiIdentity = Depends(require_mission_write), db: Session = Depends(get_db)) -> dict:
    item = dispatch_next(db)
    return {"dispatched": _mission_payload(item) if item else None}


@router.post("/mission-control/missions/{mission_id}/start", response_model=MissionOut)
def begin_mission(
    mission_id: str,
    _: ApiIdentity = Depends(require_mission_write),
    db: Session = Depends(get_db),
):
    return start_mission(db, mission_id)


@router.post("/mission-control/missions/{mission_id}/evidence", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
def record_mission_evidence(
    mission_id: str,
    payload: EvidenceCreate,
    identity: ApiIdentity = Depends(require_mission_write),
    db: Session = Depends(get_db),
):
    item = db.get(Mission, mission_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    return add_evidence(db, item, created_by=identity.role, **payload.model_dump())


@router.post("/mission-control/missions/{mission_id}/submit-verification", response_model=MissionOut)
def request_mission_verification(
    mission_id: str,
    _: ApiIdentity = Depends(require_mission_write),
    db: Session = Depends(get_db),
):
    return submit_for_verification(db, mission_id)


@router.post("/mission-control/missions/{mission_id}/verify")
def accept_mission_verification(
    mission_id: str,
    _: ApiIdentity = Depends(require_mission_verify),
    db: Session = Depends(get_db),
) -> dict:
    item, next_item = verify_mission(db, mission_id)
    return {"verified": _mission_payload(item), "next": _mission_payload(next_item) if next_item else None}


@router.post("/mission-control/missions/{mission_id}/fail")
def record_mission_failure(
    mission_id: str,
    payload: MissionFailure,
    identity: ApiIdentity = Depends(require_mission_write),
    db: Session = Depends(get_db),
) -> dict:
    item, recovery = fail_mission(
        db,
        mission_id,
        status=payload.status,
        failure_class=payload.failure_class,
        summary=payload.summary,
        root_cause=payload.root_cause,
        evidence_locator=payload.evidence_locator,
        created_by=identity.role,
    )
    return {"mission": _mission_payload(item), "recovery": _mission_payload(recovery) if recovery else None}


@router.post("/mission-control/missions/{mission_id}/fix")
def invoke_fix(
    mission_id: str,
    _: ApiIdentity = Depends(require_mission_write),
    db: Session = Depends(get_db),
) -> dict:
    return {"recovery": _mission_payload(fix_mission(db, mission_id))}


@router.post("/mission-control/missions/{mission_id}/artifacts", response_model=ArtifactOut, status_code=status.HTTP_201_CREATED)
def record_mission_artifact(
    mission_id: str,
    payload: ArtifactCreate,
    identity: ApiIdentity = Depends(require_mission_write),
    db: Session = Depends(get_db),
):
    return register_artifact(db, mission_id, created_by=identity.role, **payload.model_dump())


@router.post("/mission-control/artifacts/{artifact_id}/porter-finalize", response_model=ArtifactOut)
def finalize_mission_artifact(
    artifact_id: str,
    payload: PorterFinalize,
    identity: ApiIdentity = Depends(require_porter_write),
    db: Session = Depends(get_db),
):
    return porter_finalize(db, artifact_id, created_by=identity.role, **payload.model_dump())


@router.post("/identity/admins/{user_id}")
def promote_verified_admin(
    user_id: str,
    identity: ApiIdentity = Depends(require_admin_promotion),
    db: Session = Depends(get_db),
) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    allowed = {value.strip().casefold() for value in settings.admin_emails.split(",") if value.strip()}
    if user.email_verified_at is None or user.email.casefold() not in allowed:
        raise HTTPException(status_code=409, detail="Verified allowlisted administrator identity required")
    user.role = "admin"
    db.add(
        AuditEvent(
            user_id=user.id,
            event_type="account.admin_promoted",
            resource_type="user",
            resource_id=user.id,
            metadata_json={"authorized_by": identity.role},
        )
    )
    db.commit()
    return {"id": user.id, "role": user.role, "email_verified": True}


@router.post("/content-sources", status_code=status.HTTP_201_CREATED)
def approve_canonical_content_source(
    payload: ContentSourceCreate,
    identity: ApiIdentity = Depends(require_admin_promotion),
    db: Session = Depends(get_db),
) -> dict:
    if db.get(Book, payload.book_id) is None:
        raise HTTPException(status_code=404, detail="Book not found")
    item = CanonicalContentSource(
        **payload.model_dump(),
        status=ContentSourceStatus.approved,
        approved_by=identity.role,
        approved_at=utcnow(),
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Canonical content source is already registered")
    db.refresh(item)
    return {
        "id": item.id,
        "book_id": item.book_id,
        "source_locator": item.source_locator,
        "manifest_sha256": item.manifest_sha256,
        "chapter_hashes": item.chapter_hashes,
        "status": item.status.value,
        "approved_by": item.approved_by,
        "approval_receipt": item.approval_receipt,
        "approved_at": item.approved_at,
    }


@router.get("/doctrine", response_model=list[DoctrineOut])
def list_doctrine(
    _: ApiIdentity = Depends(require_doctrine_read),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    query = select(DoctrineEntry).order_by(DoctrineEntry.key).offset(offset).limit(limit)
    return db.scalars(query).all()


@router.post("/doctrine", response_model=DoctrineOut, status_code=status.HTTP_201_CREATED)
def create_doctrine(
    payload: DoctrineCreate,
    _: ApiIdentity = Depends(require_write),
    db: Session = Depends(get_db),
):
    item = DoctrineEntry(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Doctrine key already exists")
    db.refresh(item)
    return item


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    _: ApiIdentity = Depends(require_registry_read),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    query = select(Project).order_by(Project.name).offset(offset).limit(limit)
    return db.scalars(query).all()


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    _: ApiIdentity = Depends(require_write),
    db: Session = Depends(get_db),
):
    item = Project(**payload.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Project slug already exists")
    db.refresh(item)
    return item


@router.get("/command-briefs", response_model=list[BriefOut])
def list_briefs(
    _: ApiIdentity = Depends(require_registry_read),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
):
    query = select(CommandBrief).order_by(CommandBrief.created_at.desc()).offset(offset).limit(limit)
    return db.scalars(query).all()


@router.post("/command-briefs", response_model=BriefOut, status_code=status.HTTP_201_CREATED)
def create_brief(
    payload: BriefCreate,
    _: ApiIdentity = Depends(require_write),
    db: Session = Depends(get_db),
):
    if payload.status == BriefStatus.completed:
        raise HTTPException(status_code=409, detail="Command briefs can be completed only by verified mission evidence")
    if not db.get(Project, payload.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    item = CommandBrief(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
