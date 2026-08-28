from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import ApiIdentity, require_gateway_read, require_gateway_write
from app.db.session import get_db
from app.models.entities import GatewayRequest
from app.schemas.gateway import ExecutionStatePatch, GatewayInput
from app.services.capabilities import discover_capabilities
from app.services.command_registry import command_registry_payload
from app.services.gateway import (
    build_context_packet,
    gateway_request_payload,
    get_execution_state,
    patch_execution_state,
    resolve_gateway_request,
)


router = APIRouter(prefix="/gateway", tags=["LANSEIR gateway"])
settings = get_settings()


@router.get("/commands")
def commands(_: ApiIdentity = Depends(require_gateway_read)) -> dict:
    return {"schema_version": 1, "commands": command_registry_payload()}


@router.get("/context")
def context_packet(
    project_id: str | None = None,
    _: ApiIdentity = Depends(require_gateway_read),
    db: Session = Depends(get_db),
) -> dict:
    return build_context_packet(db, settings, project_id=project_id, repository_root=Path.cwd())


@router.get("/capabilities")
def capabilities(_: ApiIdentity = Depends(require_gateway_read)) -> dict:
    return {
        "schema_version": 1,
        "standard": "Only discovered capability is reported; named services do not imply access.",
        "adapters": discover_capabilities(settings, Path.cwd()),
    }


@router.get("/state")
def execution_state(_: ApiIdentity = Depends(require_gateway_read), db: Session = Depends(get_db)) -> dict:
    item = get_execution_state(db, settings)
    return {
        "key": item.key,
        "revision": item.revision,
        "payload": item.payload,
        "updated_by": item.updated_by,
        "updated_at": item.updated_at,
    }


@router.patch("/state")
def update_execution_state(
    payload: ExecutionStatePatch,
    identity: ApiIdentity = Depends(require_gateway_write),
    db: Session = Depends(get_db),
) -> dict:
    item = patch_execution_state(
        db,
        settings,
        expected_revision=payload.expected_revision,
        changes=payload.changes,
        actor_role=identity.role,
    )
    return {
        "key": item.key,
        "revision": item.revision,
        "payload": item.payload,
        "updated_by": item.updated_by,
        "updated_at": item.updated_at,
    }


@router.post("/resolve")
def resolve(
    payload: GatewayInput,
    identity: ApiIdentity = Depends(require_gateway_write),
    db: Session = Depends(get_db),
) -> dict:
    return resolve_gateway_request(
        db,
        settings,
        payload,
        actor_role=identity.role,
        repository_root=Path.cwd(),
    )


@router.get("/requests/{request_id}")
def request_receipt(
    request_id: str,
    _: ApiIdentity = Depends(require_gateway_read),
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(GatewayRequest, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Gateway request not found")
    return gateway_request_payload(item)
