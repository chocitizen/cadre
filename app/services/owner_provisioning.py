from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.entities import AuditEvent, User, UserSession
from app.services.identity import hash_password, normalize_email, validate_new_password


def _allowed_admins(settings: Settings) -> set[str]:
    return {normalize_email(value) for value in settings.admin_emails.split(",") if value.strip()}


def provision_owner(
    db: Session,
    settings: Settings,
    *,
    email: str,
    password: str | None = None,
    rotate_password: bool = False,
) -> dict:
    """Idempotently bootstrap an allowlisted owner without emitting credentials."""

    normalized = normalize_email(email)
    if normalized not in _allowed_admins(settings):
        raise ValueError("Owner email is not present in CADRE_ADMIN_EMAILS")
    user = db.scalar(select(User).where(User.email == normalized))
    created = user is None
    password_changed = False
    if user is None:
        if not password:
            raise ValueError("A password is required when the owner account does not exist")
        validate_new_password(password)
        user = User(
            email=normalized,
            password_hash=hash_password(password),
            display_name="Mission Control",
            role="admin",
            email_verified_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(user)
        db.flush()
        password_changed = True
    else:
        if rotate_password:
            if not password:
                raise ValueError("A password is required when rotation is requested")
            validate_new_password(password)
            user.password_hash = hash_password(password)
            db.execute(delete(UserSession).where(UserSession.user_id == user.id))
            password_changed = True
        user.role = "admin"
        user.email_verified_at = user.email_verified_at or datetime.now(timezone.utc)
        user.is_active = True

    db.add(
        AuditEvent(
            user_id=user.id,
            event_type="account.owner_provisioned",
            resource_type="user",
            resource_id=user.id,
            metadata_json={
                "mechanism": "mission_control_bootstrap",
                "created": created,
                "password_changed": password_changed,
            },
        )
    )
    db.commit()
    return {
        "status": "provisioned",
        "email": normalized,
        "role": user.role,
        "email_verified": user.email_verified_at is not None,
        "active": user.is_active,
        "created": created,
        "password_changed": password_changed,
        "credential_exposed": False,
    }


def main() -> int:
    from app.db.session import engine

    parser = argparse.ArgumentParser(description="Provision the configured CADRE owner without printing credentials.")
    parser.add_argument("--email", default="")
    parser.add_argument("--password-env", default="CADRE_OWNER_INITIAL_PASSWORD")
    parser.add_argument("--rotate-password", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    allowed = sorted(_allowed_admins(settings))
    email = normalize_email(args.email) if args.email else allowed[0] if len(allowed) == 1 else ""
    if not email:
        raise SystemExit("Provide --email when CADRE_ADMIN_EMAILS contains zero or multiple identities")
    password = os.environ.get(args.password_env) or None
    with Session(engine) as db:
        receipt = provision_owner(
            db,
            settings,
            email=email,
            password=password,
            rotate_password=args.rotate_password,
        )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
