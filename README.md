# CADRE — Sovereign Core + Governed Operations

LANSEIR remains the sovereign parent platform. This repository contains the
canonical CADRE FastAPI core plus the Hostinger operations layer authorized for
Mission Control, Al, ARC, Invictus, Porter, Griot, and Sentinel.

## Install

From the CADRE project root after extracting this package:

```bash
cp .env.example .env
```

Replace `change_me` in ignored `.env` with one strong database password in
both `CADRE_DB_PASSWORD` and the URL-encoded password inside
`CADRE_DATABASE_URL`. Replace every API token placeholder with a different
random value of at least 32 characters. Do not edit tracked Compose policy or
commit the populated file.

Then run:

```bash
docker compose up -d --build
```

Validate:

```bash
./scripts/validate.sh
```

Open:

```text
http://127.0.0.1:8000/docs
```

The API binds to loopback only. For a remote private host, use an authenticated
SSH tunnel or a separately approved HTTPS reverse proxy; do not publish port
8000 directly.

## Local development without Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export CADRE_DATABASE_URL='sqlite:///./cadre.db'
pytest -q
uvicorn app.main:app --reload
```

## M1 API

- `GET /api/v1/health`
- `GET /api/v1/doctrine`
- `POST /api/v1/doctrine`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/command-briefs`
- `POST /api/v1/command-briefs`
- `GET /api/v1/operations/state` (private/internal Mission Control read model)

`GET /api/v1/health` is public and intentionally minimal. Every other API route
requires `Authorization: Bearer <role-token>`. Mission Control and Al tokens
may write registry records; all configured CADRE role tokens may read them.
Collection routes use `limit` and `offset`, with a server-enforced maximum of
100 items per response.

## Governed Hostinger operations

The root-owned `cadre-ops` controller accepts only these named operations:

```text
status  health  deploy  validate  rollback
restart <approved-service>  logs <approved-service>
backup  backup-status  backup-verify  restore-test
release-current  release-history  system-health
security-audit  audit-verify
```

Unix identity maps to a policy role; action names, typed arguments, and service
targets are allowlisted; arbitrary shell strings are rejected. Mutations write
a durable intent before execution and a terminal hash-chained receipt after it.
The ledger uses a constant-time root-owned head checkpoint and a fail-closed
capacity ceiling.

Deploy accepts only an exact commit already contained in canonical GitHub
`main`. The root controller fetches the fixed repository, verifies ancestry,
generates the archive itself, applies extraction quotas, and binds container
health to both the Compose API service and the expected release SHA.

See `docs/HOSTINGER_OPERATIONS_RUNBOOK.md`, `docs/RECOVERY.md`, and
`SECURITY.md` before installation or production activation.

## Security boundary

The authenticated application API remains private. The production proxy publishes only
`/healthz` over HTTPS and returns `404` for every other public path. PostgreSQL,
the operations interface, Mission Control state, Docker control, and deferred
AI administration are not exposed publicly.
