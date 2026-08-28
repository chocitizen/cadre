from __future__ import annotations

import json
import secrets
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


KNOWN_ROLES = {
    "mission_control",
    "al",
    "arc",
    "invictus",
    "porter",
    "griot",
    "sentinel",
}
READ_ROLES = frozenset(KNOWN_ROLES)
WRITE_ROLES = frozenset({"mission_control", "al"})


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


require_read = require_roles(*sorted(READ_ROLES))
require_write = require_roles(*sorted(WRITE_ROLES))
