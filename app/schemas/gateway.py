from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class GatewayInput(BaseModel):
    raw_input: str = Field(min_length=1, max_length=100_000)
    interface: str = Field(default="api", pattern=r"^[a-z][a-z0-9_-]{1,79}$")
    operating_mode: Literal["founder", "client"] = "founder"
    project_id: str | None = Field(default=None, max_length=64)
    reference_id: str | None = Field(default=None, max_length=64)
    execute: bool = True

    @field_validator("raw_input")
    @classmethod
    def reject_blank_input(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("raw_input cannot be blank")
        return value


class ExecutionStatePatch(BaseModel):
    expected_revision: int = Field(ge=1)
    changes: dict[str, Any] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def bound_changes(self):
        allowed = {
            "active_project",
            "current_milestone",
            "current_objective",
            "approved_decisions",
            "locked_assets",
            "work_in_progress",
            "completed_work",
            "blocked_work",
            "next_executable_work",
            "assigned_agents",
            "deployment_state",
            "environment_state",
            "relevant_services",
            "last_validated_commit",
            "last_deployment",
            "production_acceptance",
            "delivered_artifact_ids",
            "last_signal_action",
            "rollback_reference",
        }
        unknown = set(self.changes) - allowed
        if unknown:
            raise ValueError(f"Unsupported execution-state fields: {', '.join(sorted(unknown))}")
        return self
