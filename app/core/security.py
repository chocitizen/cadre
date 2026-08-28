from __future__ import annotations

import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import User
from app.services.identity import require_csrf, resolve_session


KNOWN_ROLES = {
    "mission_control",
    "al",
    "arc",
    "invictus",
    "porter",
    "griot",
    "sentinel",
}
WRITE_ROLES = frozenset({"mission_control", "al"})
DOCTRINE_READ_ROLES = frozenset({"mission_control", "al", "griot"})
REGISTRY_READ_ROLES = frozenset({"mission_control", "al", "griot"})
OPERATIONS_READ_ROLES = frozenset({"mission_control", "al"})
MISSION_READ_ROLES = frozenset({"mission_control", "al", "invictus", "porter", "griot", "sentinel"})
MISSION_WRITE_ROLES = frozenset({"mission_control", "al"})
PORTER_WRITE_ROLES = frozenset({"mission_control", "porter"})
MISSION_VERIFY_ROLES = frozenset({"mission_control", "griot"})


@dataclass(frozen=True)
class ApiIdentity:
    role: str


def _configured_tokens() -> dict[str, str]:
    raw = get_settings().api_tokens_json
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API identity policy is unavailable",
        ) from exc
    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API identity policy is unavailable",
        )
    if set(parsed) - KNOWN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API identity policy is unavailable",
        )
    tokens = {}
    for role, token in parsed.items():
        if not isinstance(token, str) or len(token) < 32 or len(set(token)) < 10 or "$" in token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API identity policy is unavailable",
            )
        tokens[role] = token
    if not tokens or len(set(tokens.values())) != len(tokens):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API identity policy is unavailable",
        )
    return tokens


def require_roles(*allowed_roles: str) -> Callable[[Request], ApiIdentity]:
    allowed = frozenset(allowed_roles)

    def dependency(request: Request) -> ApiIdentity:
        authorization = request.headers.get("authorization", "")
        scheme, separator, presented = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not presented:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Service identity required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        matched_role = None
        for role, configured in _configured_tokens().items():
            if secrets.compare_digest(presented, configured):
                matched_role = role
        if matched_role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service identity",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if matched_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service role is not authorized for this operation",
            )
        return ApiIdentity(role=matched_role)

    return dependency


require_write = require_roles(*sorted(WRITE_ROLES))
require_doctrine_read = require_roles(*sorted(DOCTRINE_READ_ROLES))
require_registry_read = require_roles(*sorted(REGISTRY_READ_ROLES))
require_operations_read = require_roles(*sorted(OPERATIONS_READ_ROLES))
require_mission_read = require_roles(*sorted(MISSION_READ_ROLES))
require_mission_write = require_roles(*sorted(MISSION_WRITE_ROLES))
require_porter_write = require_roles(*sorted(PORTER_WRITE_ROLES))
require_mission_verify = require_roles(*sorted(MISSION_VERIFY_ROLES))
require_admin_promotion = require_roles("mission_control")


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    resolved = resolve_session(db, request)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    return resolved[1]


def require_user_write(request: Request, db: Session = Depends(get_db)) -> User:
    resolved = resolve_session(db, request)
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    session, user = resolved
    require_csrf(request, session)
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin" or user.email_verified_at is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


def require_admin_write(request: Request, db: Session = Depends(get_db)) -> User:
    user = require_user_write(request, db)
    if user.role != "admin" or user.email_verified_at is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user
