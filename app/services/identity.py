from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import AuditEvent, User, UserSession


SESSION_COOKIE = "lanseir_session"
CSRF_COOKIE = "lanseir_csrf"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(derived).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=base64.urlsafe_b64decode(salt.encode()),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=64,
        )
        return hmac.compare_digest(base64.urlsafe_b64encode(derived).decode(), expected)
    except (ValueError, TypeError):
        return False


def validate_new_password(password: str) -> None:
    if len(password) < 12 or not (
        any(c.islower() for c in password)
        and any(c.isupper() for c in password)
        and any(c.isdigit() for c in password)
    ):
        raise HTTPException(status_code=422, detail="Password must be at least 12 characters with upper-case, lower-case, and numeric characters")


def _secure_cookie() -> bool:
    return get_settings().env.casefold() == "production"


def issue_session(db: Session, response: Response, user: User) -> str:
    raw_token = secrets.token_urlsafe(48)
    raw_csrf = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(days=get_settings().session_days)
    session = UserSession(
        user_id=user.id,
        token_hash=token_hash(raw_token),
        csrf_hash=token_hash(raw_csrf),
        expires_at=expires,
    )
    db.add(session)
    db.flush()
    secure = _secure_cookie()
    max_age = get_settings().session_days * 86_400
    response.set_cookie(SESSION_COOKIE, raw_token, httponly=True, secure=secure, samesite="lax", max_age=max_age, path="/")
    response.set_cookie(CSRF_COOKIE, raw_csrf, httponly=False, secure=secure, samesite="lax", max_age=max_age, path="/")
    return raw_csrf


def clear_session(db: Session, request: Request, response: Response) -> None:
    raw = request.cookies.get(SESSION_COOKIE)
    if raw:
        db.execute(delete(UserSession).where(UserSession.token_hash == token_hash(raw)))
    response.delete_cookie(SESSION_COOKIE, path="/", secure=_secure_cookie(), samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/", secure=_secure_cookie(), samesite="lax")


def resolve_session(db: Session, request: Request) -> tuple[UserSession, User] | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash(raw)))
    if session is None or _aware(session.expires_at) <= utcnow():
        if session is not None:
            db.delete(session)
            db.commit()
        return None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    session.last_seen_at = utcnow()
    db.commit()
    return session, user


def require_csrf(request: Request, session: UserSession) -> None:
    presented = request.headers.get("x-csrf-token", "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if not presented or not cookie or not hmac.compare_digest(presented, cookie) or not hmac.compare_digest(token_hash(presented), session.csrf_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


def audit(db: Session, request: Request, event_type: str, user_id: str | None = None, resource_type: str | None = None, resource_id: str | None = None, metadata: dict | None = None) -> None:
    db.add(
        AuditEvent(
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=getattr(request.state, "request_id", None),
            metadata_json=metadata or {},
        )
    )
    db.commit()
