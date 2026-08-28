from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CommandSpec:
    key: str
    aliases: tuple[str, ...]
    intent: str
    action: str
    approval_required: bool = False


COMMAND_SPECS = (
    CommandSpec(
        "signal",
        ("SIGNAL",),
        "Dispatch the currently staged deliverable or action.",
        "dispatch_staged",
    ),
    CommandSpec(
        "now",
        ("NOW", "GO"),
        "Move immediately to the current executable action.",
        "dispatch_next",
    ),
    CommandSpec(
        "advance",
        ("ADVANCE", "ACT"),
        "Continue the approved workflow from canonical state.",
        "dispatch_next",
    ),
    CommandSpec(
        "actively_advance",
        ("ACTIVELY ADVANCE",),
        "Move approved work into implementation using available automation.",
        "dispatch_next",
    ),
    CommandSpec(
        "deploy",
        ("DEPLOY",),
        "Package, validate, and stage the current deployment-ready implementation.",
        "deploy_staging",
    ),
    CommandSpec(
        "approve_lock",
        ("+",),
        "Approve and lock the explicitly referenced decision or Command Brief.",
        "approve_reference",
        approval_required=True,
    ),
    CommandSpec(
        "status",
        ("STATUS",),
        "Return actual system state, evidence, blockers, and the next action.",
        "report_status",
    ),
    CommandSpec(
        "resolve_continue",
        ("YOU KNOW WHAT TO DO",),
        "Resolve canonical state and continue the obvious approved next action.",
        "dispatch_next",
    ),
)


def normalize_input(raw_input: str) -> str:
    stripped = raw_input.strip()
    if stripped == "+":
        return "+"
    return " ".join(re.sub(r"[^A-Za-z0-9]+", " ", stripped).upper().split())


def resolve_command(raw_input: str) -> CommandSpec | None:
    normalized = normalize_input(raw_input)
    return next((spec for spec in COMMAND_SPECS if normalized in spec.aliases), None)


def command_registry_payload() -> list[dict]:
    return [asdict(spec) for spec in COMMAND_SPECS]
