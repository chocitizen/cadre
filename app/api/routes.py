from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import CommandBrief, DoctrineEntry, Project
from app.schemas.entities import BriefCreate, BriefOut, DoctrineCreate, DoctrineOut, ProjectCreate, ProjectOut

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "system": "CADRE", "milestone": "M1", "version": "0.1.0"}


@router.get("/doctrine", response_model=list[DoctrineOut])
def list_doctrine(db: Session = Depends(get_db)):
    return db.scalars(select(DoctrineEntry).order_by(DoctrineEntry.key)).all()


@router.post("/doctrine", response_model=DoctrineOut, status_code=status.HTTP_201_CREATED)
def create_doctrine(payload: DoctrineCreate, db: Session = Depends(get_db)):
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
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(Project).order_by(Project.name)).all()


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
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
def list_briefs(db: Session = Depends(get_db)):
    return db.scalars(select(CommandBrief).order_by(CommandBrief.created_at.desc())).all()


@router.post("/command-briefs", response_model=BriefOut, status_code=status.HTTP_201_CREATED)
def create_brief(payload: BriefCreate, db: Session = Depends(get_db)):
    if not db.get(Project, payload.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    item = CommandBrief(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
