from datetime import datetime
from typing import Any
import json
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.entities import ArtifactState, BriefStatus, MissionStatus, ProjectStatus


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


class MissionCreate(BoundedModel):
    command_brief_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=2, max_length=240)
    action_key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,79}$")
    specialist_key: str = Field(default="al", pattern=r"^[a-z][a-z0-9_]{1,79}$")
    priority: int = Field(default=50, ge=0, le=100)
    dependency_ids: list[str] = Field(default_factory=list, max_length=100)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[Any] = Field(default_factory=list, max_length=100)
    validation_criteria: list[Any] = Field(default_factory=list, min_length=1, max_length=100)
    max_retries: int = Field(default=1, ge=0, le=3)


class MissionOut(MissionCreate, ORMModel):
    id: str
    recovery_for_id: str | None
    status: MissionStatus
    failure_class: str | None
    root_cause: str
    retry_count: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    verified_at: datetime | None


class EvidenceCreate(BoundedModel):
    kind: str = Field(
        pattern=r"^(artifact_created|code_committed|test_passed|deployment_completed|dependency_resolved|milestone_completed|verification_passed|failure_captured|diagnosis|repair_completed|archive_completed|cleanup_completed)$"
    )
    summary: str = Field(min_length=3, max_length=10_000)
    locator: str = Field(default="", max_length=500)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    passed: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class EvidenceOut(EvidenceCreate, ORMModel):
    id: str
    mission_id: str
    created_by: str
    created_at: datetime


class MissionFailure(BoundedModel):
    status: MissionStatus = MissionStatus.failed
    failure_class: str = Field(pattern=r"^(deterministic|transient|dependency|authorization|policy|unknown)$")
    summary: str = Field(min_length=3, max_length=10_000)
    root_cause: str = Field(default="", max_length=20_000)
    evidence_locator: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def require_failure_status(self):
        allowed = {
            MissionStatus.failed,
            MissionStatus.blocked,
            MissionStatus.stalled,
            MissionStatus.verification_failed,
        }
        if self.status not in allowed:
            raise ValueError("Failure status must expose FIX")
        return self


class ArtifactCreate(BoundedModel):
    name: str = Field(min_length=1, max_length=240)
    source_locator: str = Field(min_length=1, max_length=500)
    destination_locator: str = Field(default="", max_length=500)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class ArtifactOut(ArtifactCreate, ORMModel):
    id: str
    mission_id: str
    archive_locator: str
    state: ArtifactState
    source_cleaned: bool
    created_at: datetime
    updated_at: datetime


class PorterFinalize(BoundedModel):
    destination_locator: str = Field(min_length=1, max_length=500)
    archive_locator: str = Field(min_length=1, max_length=500)
    source_cleaned: bool = False
    verification_summary: str = Field(min_length=3, max_length=10_000)


class ContentSourceCreate(BoundedModel):
    book_id: str = Field(min_length=1, max_length=36)
    source_locator: str = Field(min_length=1, max_length=500)
    manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    chapter_hashes: dict[str, str] = Field(min_length=1, max_length=10_000)
    approval_receipt: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_chapter_hashes(self):
        if any(not key.isdigit() or int(key) < 1 for key in self.chapter_hashes):
            raise ValueError("Chapter hash keys must be positive chapter positions")
        if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in self.chapter_hashes.values()):
            raise ValueError("Chapter hashes must be lowercase SHA-256 values")
        return self
