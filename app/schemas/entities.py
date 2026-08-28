from datetime import datetime
from typing import Any
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.entities import BriefStatus, ProjectStatus


MAX_RECORD_BYTES = 256_000
MAX_JSON_DEPTH = 8


def _json_depth(value, depth: int = 0) -> int:
    if depth > MAX_JSON_DEPTH:
        return depth
    if isinstance(value, dict):
        return max((_json_depth(item, depth + 1) for item in value.values()), default=depth)
    if isinstance(value, list):
        return max((_json_depth(item, depth + 1) for item in value), default=depth)
    return depth


class BoundedModel(BaseModel):
    @model_validator(mode="after")
    def enforce_aggregate_bounds(self):
        payload = self.model_dump(mode="json")
        if _json_depth(payload) > MAX_JSON_DEPTH:
            raise ValueError(f"JSON nesting exceeds {MAX_JSON_DEPTH} levels")
        if len(json.dumps(payload, separators=(",", ":")).encode("utf-8")) > MAX_RECORD_BYTES:
            raise ValueError(f"Record exceeds {MAX_RECORD_BYTES} bytes")
        return self


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DoctrineCreate(BoundedModel):
    key: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=1, max_length=100_000)
    category: str = Field(default="principle", max_length=100)
    version: str = Field(default="1.0", max_length=32)
    is_active: bool = True


class DoctrineOut(DoctrineCreate, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BoundedModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=120)
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=50_000)
    status: ProjectStatus = ProjectStatus.active
    source_of_truth: dict[str, Any] = Field(default_factory=dict, max_length=100)


class ProjectOut(ProjectCreate, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


class BriefCreate(BoundedModel):
    project_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=2, max_length=240)
    objective: str = Field(min_length=1, max_length=100_000)
    authority: str = Field(default="Master Operating Doctrine", max_length=200)
    current_state: str = Field(default="", max_length=50_000)
    constraints: list[Any] = Field(default_factory=list, max_length=100)
    dependencies: list[Any] = Field(default_factory=list, max_length=100)
    expected_outputs: list[Any] = Field(default_factory=list, max_length=100)
    validation_criteria: list[Any] = Field(default_factory=list, max_length=100)
    source_refs: list[Any] = Field(default_factory=list, max_length=100)
    specialist_roles: list[Any] = Field(default_factory=list, max_length=100)
    status: BriefStatus = BriefStatus.draft


class BriefOut(BriefCreate, ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime
