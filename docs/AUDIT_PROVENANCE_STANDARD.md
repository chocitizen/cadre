# Audit and Provenance Standard

Every gateway request creates a durable receipt containing the request digest,
resolved command/intent, active context, specialist plan, capability routing,
actions attempted and completed, validation, blockers, artifacts, release or
deployment identifiers when available, status, and next executable action.

Full request content is not retained. The receipt hash supports
correlation without expanding the prompt-content exposure boundary. Audit events
record the receipt identifier, actor role, command, status, and request hash.

Every state mutation increments the execution-state revision and records the
actor. Stale writes fail closed. Material mission completion remains governed by
Mission Evidence and Griot/Mission Control verification; a gateway receipt does
not replace delivery evidence.

Commit, CI, staging, production, and rollback are separate provenance facts.
Never infer deployment from a successful build, infer remote publication from a
local commit, or infer provider readiness from configuration alone.
