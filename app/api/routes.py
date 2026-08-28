import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import get_settings
from app.core.security import ApiIdentity, require_read, require_write
from app.models.entities import CommandBrief, DoctrineEntry, Project
from app.schemas.entities import BriefCreate, BriefOut, DoctrineCreate, DoctrineOut, ProjectCreate, ProjectOut

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "system": "CADRE",
        "milestone": "M1",
        "version": "0.2.0",
        "release": settings.release_id,
    }


@router.get("/operations/state")
def operations_state(_: ApiIdentity = Depends(require_read)) -> dict:
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


@router.get("/doctrine", response_model=list[DoctrineOut])
def list_doctrine(
    _: ApiIdentity = Depends(require_read),
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
    _: ApiIdentity = Depends(require_read),
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
    _: ApiIdentity = Depends(require_read),
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
    if not db.get(Project, payload.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    item = CommandBrief(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
