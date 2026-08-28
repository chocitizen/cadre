# LANSEIR — Sovereign Platform

LANSEIR is the sovereign parent platform. CADRE is its internal execution
system: Mission Control, Al, ARC, Invictus, Porter, Griot, Sentinel, and the
specialist registry. The repository combines the private operating core with a
public-facing, mobile-first LANSEIR product experience.

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

## Product and internal APIs

- Public product: identity, account control/export/deletion, library,
  entitlements, reading progress, bookmarks, notes, Captain's Log, Voyages,
  Support, and the LANSEIR Guide.
- Private CADRE: doctrine, projects, Command Briefs, Mission Control, specialist
  dispatch, evidence verification, recovery/FIX, provenance, and Porter
  lifecycle records.
- Minimal public health: `GET /api/v1/health` and the proxy alias `/healthz`.

Product routes use secure server sessions and CSRF protection for mutations.
Internal routes require a role-scoped service bearer token and are denied by
the production proxy. Administrator status is never inferred from signup: a
verified, configured email must be explicitly promoted by Mission Control.
VESSEL chapters can be installed only when their content hash matches an
approved canonical source record.

Mission completion is evidence-gated. Status messages do not count as progress;
failed, blocked, stalled, or verification-failed missions expose FIX. A
deterministic failure dispatches an Al recovery mission before the bounded retry
of the original action. See `docs/MISSION_EXECUTION_STANDARD.md`.

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

See `docs/HOSTINGER_OPERATIONS_RUNBOOK.md`, `docs/DEPLOYMENT_SOP.md`,
`docs/RECOVERY.md`, `docs/PORTER_SOP.md`, and `SECURITY.md` before production
activation.

## Security boundary

The production proxy publishes the LANSEIR product and `/healthz` over HTTPS.
Doctrine, registries, Mission Control, admin/content-source endpoints,
PostgreSQL, Docker control, and operations state remain internal. The default
Guide is local and provider-free. LiteLLM/OpenRouter activation remains blocked
until credentials, service health, routing policy, and provider provenance are
validated without exposing secrets.
