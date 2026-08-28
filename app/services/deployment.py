from __future__ import annotations

from urllib.parse import urlparse


PRODUCTION_READINESS_GATES = (
    "production_build_successful",
    "production_environment_configured",
    "public_endpoint_resolved",
    "required_services_operational",
    "owner_account_provisioned",
    "production_authentication_verified",
    "protected_interface_smoke_tested",
    "critical_user_journey_validated",
    "credential_delivery_approved",
    "rollback_available",
)


def _https_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme == "https" and bool(parsed.hostname)


def assess_production_readiness(evidence: dict | None) -> dict:
    """Return a secret-free, fail-closed production acceptance decision."""

    evidence = evidence if isinstance(evidence, dict) else {}
    gates = {key: evidence.get(key) is True for key in PRODUCTION_READINESS_GATES}
    gates["exact_login_url_captured"] = _https_url(evidence.get("live_login_url"))
    gates["owner_identity_recorded"] = bool(str(evidence.get("owner_email", "")).strip())
    missing = [key for key, passed in gates.items() if not passed]
    ready = not missing
    return {
        "status": "READY" if ready else "NOT_READY",
        "ready": ready,
        "gates": gates,
        "missing": missing,
        "live_login_url": evidence.get("live_login_url") if gates["exact_login_url_captured"] else None,
        "owner_email": str(evidence.get("owner_email", "")).strip().casefold() or None,
    }
