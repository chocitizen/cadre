# CADRE M1 — Sovereign Core Foundation

Version: 0.1.0
Status: Canonical current core
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

## Deliberately deferred

- LiteLLM / OpenRouter / model routing
- Specialist registry and dynamic council assembly
- LANSEIR orchestration/state machine
- Institutional memory promotion engine
- Mission Control UI
- Ready Dock / notifications
- VESSEL application integration

These belong to later milestones and are excluded to preserve M1 KISS discipline.

## Canonical M1 acceptance criteria

1. The stack starts from the project root with Docker Compose.
2. PostgreSQL becomes healthy.
3. CADRE API responds at `/api/v1/health`.
4. Approved doctrine seed entries are readable.
5. Projects can be created/read.
6. Command briefs can be created/read and are bound to projects.
7. Swagger/OpenAPI documentation is available at `/docs`.
8. The unauthenticated M1 API binds to host loopback only.
9. Credentials and preserved local state are excluded from the Docker image.
