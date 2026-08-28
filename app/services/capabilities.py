from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings


@dataclass(frozen=True)
class Capability:
    name: str
    state: str
    mode: str
    approval: str = "policy_driven"

    def payload(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "mode": self.mode,
            "approval": self.approval,
        }


def _service_payload(
    service: str,
    configured: bool,
    capabilities: list[Capability],
    blockers: list[str],
) -> dict:
    states = {item.state for item in capabilities}
    status = (
        "ready"
        if states == {"ready"}
        else "partial"
        if states & {"ready", "configured_unverified"}
        else "blocked"
    )
    return {
        "service": service,
        "configured": configured,
        "status": status,
        "capabilities": [item.payload() for item in capabilities],
        "blockers": blockers,
    }


def discover_github(settings: Settings, repository_root: Path | None = None) -> dict:
    repository_root = repository_root or Path.cwd()
    local_repository = (repository_root / ".git").exists() and shutil.which("git") is not None
    remote_configured = bool(settings.github_repository.strip())
    authenticated = bool(settings.github_token.strip())
    blockers = []
    if not local_repository:
        blockers.append("Git repository and executable were not both discovered in the runtime.")
    if not remote_configured:
        blockers.append("CADRE_GITHUB_REPOSITORY is not configured.")
    if not authenticated:
        blockers.append("A GitHub service credential is not configured for remote mutation.")
    return _service_payload(
        "github",
        local_repository or remote_configured,
        [
            Capability("repository.read", "ready" if local_repository else "blocked", "read", "none"),
            Capability("branch.create", "ready" if local_repository else "blocked", "write"),
            Capability("commit.create", "ready" if local_repository else "blocked", "write"),
            Capability("remote.push", "ready" if remote_configured and authenticated else "blocked", "write"),
            Capability("pull_request.manage", "ready" if remote_configured and authenticated and shutil.which("gh") else "blocked", "write"),
        ],
        blockers,
    )


def discover_railway(settings: Settings) -> dict:
    cli_available = shutil.which("railway") is not None
    configured = bool(settings.railway_project_id.strip())
    authenticated = bool(settings.railway_token.strip())
    ready = cli_available and configured and authenticated
    blockers = []
    if not cli_available:
        blockers.append("Railway CLI was not discovered in the runtime.")
    if not configured:
        blockers.append("CADRE_RAILWAY_PROJECT_ID is not configured.")
    if not authenticated:
        blockers.append("A Railway service credential is not configured.")
    return _service_payload(
        "railway",
        configured,
        [
            Capability("staging.inspect", "ready" if ready else "blocked", "read"),
            Capability("staging.deploy", "ready" if ready else "blocked", "write", "approved_brief"),
            Capability("staging.verify_http", "ready" if ready else "blocked", "read", "none"),
        ],
        blockers,
    )


def discover_openrouter(settings: Settings) -> dict:
    selected = settings.ai_provider.casefold() == "openrouter"
    authenticated = bool(settings.ai_api_key.strip())
    ready = selected and authenticated
    blockers = []
    if not selected:
        blockers.append("OpenRouter is not the active CADRE AI provider.")
    if not authenticated:
        blockers.append("An OpenRouter credential is not configured.")
    return _service_payload(
        "openrouter",
        selected,
        [
            Capability("models.route", "ready" if ready else "blocked", "write"),
            Capability("provider.health", "configured_unverified" if ready else "blocked", "read", "none"),
        ],
        blockers,
    )


def discover_litellm(settings: Settings) -> dict:
    selected = settings.ai_provider.casefold() == "litellm"
    endpoint_configured = bool(settings.ai_base_url.strip())
    cli_available = shutil.which("litellm") is not None
    configured = selected and endpoint_configured
    blockers = []
    if not selected:
        blockers.append("LiteLLM is not the active CADRE AI provider.")
    if not endpoint_configured:
        blockers.append("The LiteLLM gateway endpoint is not configured.")
    if not cli_available:
        blockers.append("LiteLLM CLI was not discovered in the runtime.")
    return _service_payload(
        "litellm",
        configured,
        [
            Capability("gateway.route", "configured_unverified" if configured else "blocked", "write"),
            Capability("gateway.health", "configured_unverified" if configured else "blocked", "read", "none"),
            Capability("gateway.admin", "ready" if configured and cli_available else "blocked", "write"),
        ],
        blockers,
    )


def discover_hostinger(settings: Settings) -> dict:
    configured = settings.hostinger_operations_enabled and bool(settings.hostinger_ssh_host.strip())
    blockers = []
    if not settings.hostinger_operations_enabled:
        blockers.append("Hostinger operations are disabled by policy.")
    if not settings.hostinger_ssh_host.strip():
        blockers.append("A Hostinger SSH host alias is not configured.")
    return _service_payload(
        "hostinger",
        configured,
        [
            Capability("production.status", "ready" if configured else "blocked", "read", "none"),
            Capability("production.deploy", "ready" if configured else "blocked", "write", "explicit_production_approval"),
            Capability("production.rollback", "ready" if configured else "blocked", "write", "incident_or_explicit_approval"),
        ],
        blockers,
    )


def discover_capabilities(settings: Settings, repository_root: Path | None = None) -> list[dict]:
    return [
        discover_github(settings, repository_root),
        discover_railway(settings),
        discover_openrouter(settings),
        discover_litellm(settings),
        discover_hostinger(settings),
    ]


def capability_ready(discovery: list[dict], service: str, capability: str) -> bool:
    record = next((item for item in discovery if item["service"] == service), None)
    if record is None:
        return False
    item = next((value for value in record["capabilities"] if value["name"] == capability), None)
    return bool(item and item["state"] == "ready")
