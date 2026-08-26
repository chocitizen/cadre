from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.entities import BriefStatus, ProjectStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DoctrineCreate(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=1)
    category: str = "principle"
    version: str = "1.0"
    is_active: bool = True


class DoctrineOut(DoctrineCreate, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=120)
    name: str = Field(min_length=2, max_length=200)
    description: str = ""
    status: ProjectStatus = ProjectStatus.active
    source_of_truth: dict[str, Any] = Field(default_factory=dict)


class ProjectOut(ProjectCreate, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


class BriefCreate(BaseModel):
    project_id: str
    title: str = Field(min_length=2, max_length=240)
    objective: str = Field(min_length=1)
    authority: str = "Master Operating Doctrine"
    current_state: str = ""
    constraints: list[Any] = Field(default_factory=list)
    dependencies: list[Any] = Field(default_factory=list)
    expected_outputs: list[Any] = Field(default_factory=list)
    validation_criteria: list[Any] = Field(default_factory=list)
    source_refs: list[Any] = Field(default_factory=list)
    specialist_roles: list[Any] = Field(default_factory=list)
    status: BriefStatus = BriefStatus.draft


class BriefOut(BriefCreate, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime
