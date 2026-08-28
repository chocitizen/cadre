# LANSEIR M3 — Universal Execution Gateway

Version: 0.4.0
Status: Locally validated LANSEIR platform candidate; remote/live gates pending
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
- LANSEIR mobile-first product shell with account portability and deletion
- Evidence-gated mission state machine and specialist dispatch
- Deterministic Al recovery and browser/API FIX controls
- Mission artifacts with Porter install/register/archive/cleanup receipts
- Approved-source hashes and per-chapter provenance for protected VESSEL content
- Byte-verified LANSEIR/CADRE foundation records and repository registry
- Universal Prompt Gateway with durable command semantics and context packets
- Persistent versioned execution state and privacy-aware gateway audit receipts
- Specialist-authority routing and Al sovereign engineering operator charter
- Capability-discovering GitHub, Railway, OpenRouter, LiteLLM, and Hostinger adapters
- Railway staging, model-routing, security, provenance, and recovery SOPs

## Deliberately deferred or externally gated

- Live LiteLLM / OpenRouter provider activation
- Live Railway project binding, deployment, URL, and responsive acceptance
- Remote AI/model execution and credential validation
- Institutional memory promotion engine
- Protected-main approval and merge
- Ready Dock / notifications
- Authorized VESSEL manuscript/audio ingestion and publication

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
8. Internal CADRE/admin APIs bind privately; only the approved LANSEIR product routes and health are public in production.
9. Credentials and preserved local state are excluded from the Docker image.
10. Operations reject unmapped actors, unlisted actions, and unapproved targets.
11. Mutations write durable audit intent and terminal receipts form a verifiable hash chain.
12. Release state distinguishes queued, building, validating, live, rolled back,
    and failed outcomes.
13. Deploy accepts only a full commit SHA verified as an ancestor of canonical GitHub `main`.
14. Production health is bound to the Compose API service and active release SHA.
15. A mission cannot complete without material evidence and an explicit passed verification record.
16. Protected content cannot be published without an approved canonical source and matching chapter hashes.
17. Porter refuses source cleanup until destination and archive evidence exist and at least one other registered copy remains.
18. Foundation package hashes and Source-of-Truth registry membership validate without drift.
19. Short founder commands resolve against canonical state and never infer missing approval.
20. Gateway receipts, state revisions, specialist plans, blockers, and next actions persist.
21. Service adapters never claim capability from a service name or expose credentials.
22. Railway staging cannot dispatch without proven adapter capability and an approved deployment mission.
