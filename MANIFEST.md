# CADRE M1 — Sovereign Core Foundation

Version: 0.2.0
Status: Canonical core with proposed Hostinger operations release
Package rule: extract directly at the CADRE project root; no wrapper directory is required.

Promotion and rollback provenance are recorded in `CANONICAL_STATUS.md`.

## Included

- FastAPI sovereign core service
- PostgreSQL persistence via Docker Compose
- Doctrine Registry with approved governing seed entries
- Project Registry
- Command Brief Registry
- Health endpoint
- Automatic schema initialization
- API documentation at `/docs`
- Local test path using SQLite
- Validation script
- Environment template
- Configuration-driven registry for Mission Control, Al, ARC, Invictus,
  Porter, Griot, and Sentinel
- Root-owned, role-aware, action- and service-allowlisted operations controller
- Authenticated, role-authorized private API with bounded requests and pagination
- Write-ahead intent and terminal hash-chained receipts with constant-time head policy
- Canonical-Git-verified immutable releases, atomic current/previous pointers,
  release-bound health gating, and verified fallback to the last known-good release
- Streamed database/state/policy backup, capacity/frequency controls, integrity
  verification, and isolated restore test
- Private application/data/operations networks and a public HTTPS health-only boundary
- Systemd schedules for Sentinel health observation and Porter backups
- GitHub validation workflow; production delivery activation remains separately gated

## Deliberately deferred or externally gated

- LiteLLM / OpenRouter / model routing
- Dynamic council assembly beyond the governed role registry
- Remote AI/model execution
- Institutional memory promotion engine
- Mission Control UI beyond the internal state API
- Ready Dock / notifications
- VESSEL application integration

ARC remains represented but blocked until an approved LiteLLM/model-routing
service is installed and explicitly enabled. Hostinger installation, HTTPS,
external-port checks, backup execution, restore testing, and cross-system
delivery require live VPS access and cannot be claimed from repository tests.

## Canonical M1 acceptance criteria

1. The stack starts from the project root with Docker Compose.
2. PostgreSQL becomes healthy.
3. CADRE API responds at `/api/v1/health`.
4. Approved doctrine seed entries are readable.
5. Projects can be created/read.
6. Command briefs can be created/read and are bound to projects.
7. Swagger/OpenAPI documentation is available at `/docs`.
8. The authenticated M1 API binds to host loopback only in development; only health is public in production.
9. Credentials and preserved local state are excluded from the Docker image.
10. Operations reject unmapped actors, unlisted actions, and unapproved targets.
11. Mutations write durable audit intent and terminal receipts form a verifiable hash chain.
12. Release state distinguishes queued, building, validating, live, rolled back,
    and failed outcomes.
13. Deploy accepts only a full commit SHA verified as an ancestor of canonical GitHub `main`.
14. Production health is bound to the Compose API service and active release SHA.
