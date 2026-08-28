# LANSEIR / CADRE

LANSEIR is the sovereign product layer. CADRE is its internal operating system.
This repository contains the FastAPI product, persistence model, private user
experiences, inspectable AI routing, Mission Control, and governed Hostinger
operations controller.

Current repository milestone: **M2 / 0.3.0 release candidate**. It is locally
validated but not represented as live production. See `CANONICAL_STATUS.md`
and `docs/EXTERNAL_DEPENDENCY_PACKET.md` for the exact boundary.

## Product capabilities

- Responsive public and authenticated shells, legal/support paths, loading,
  empty, error, success, and not-found states
- Database-backed signup, sign-in/out, session restoration, password change,
  reset/verification token lifecycle, profile, export, and deletion APIs
- HttpOnly opaque sessions, double-submit CSRF, role-aware admin access,
  ownership checks, request IDs, rate/resource limits, and security headers
- VESSEL library metadata, entitlements, chapters, reading/audio position,
  notes, and bookmarks; manuscript/audio remain gated to authorized sources
- Private Captain's Log CRUD and search
- Stateful sequential Voyages with reflections and resumable progress
- Persistent Reflection Guide conversations with a zero-cost local provider
  and an opt-in OpenAI-compatible provider abstraction
- Specialist registry, observable agent runs, actual failure states, audit
  events, support intake, and authorization-protected Mission Control
- Additive migration ledger preserving M1 registry data
- Root-owned, typed, allowlisted Hostinger operations with release-bound
  health, fail-closed audit evidence, backup/restore controls, and rollback

## Local development

Python 3.12 is the validated runtime.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'pip==26.2.1'
python -m pip install -e '.[dev]'
cp .env.example .env
```

For a zero-infrastructure local run, set an ignored `.env`:

```text
CADRE_ENV=development
CADRE_DATABASE_URL=sqlite:///./cadre.db
CADRE_ADMIN_EMAILS=owner@example.com
CADRE_AI_PROVIDER=local
```

Start and validate:

```bash
./scripts/validate.sh
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/`. Development API documentation is available at
`/docs`; production disables Swagger, ReDoc, and OpenAPI schema routes.

## Environment policy

All names use the `CADRE_` prefix. Populate only ignored `.env` or the
root-owned production secret file; never commit values.

Required in production:

- `CADRE_DATABASE_URL`
- `CADRE_API_TOKENS_JSON`
- `CADRE_ADMIN_EMAILS`
- `CADRE_RELEASE_ID`
- Host policy values in `ops/config/cadre.env.example`

AI routing defaults to `local` and incurs no provider cost. Remote routing is
inactive unless `CADRE_AI_PROVIDER`, `CADRE_AI_MODEL`, `CADRE_AI_BASE_URL`, and
the server-side `CADRE_AI_API_KEY` are explicitly configured. HTTPS is
required except for a loopback model gateway. The browser never receives the
provider credential.

## Data and migrations

Startup calls `app.db.migrations.run_migrations`. M2 is additive: it creates
new tables/indexes and records `20260828_01_lanseir_product_spine`; it does not
rewrite or delete M1 registry data. Future destructive or column-altering work
requires explicit migration SQL and a verified backup.

Primary durable domains are users/sessions, books/chapters/entitlements,
reading state, notes/bookmarks, private journals, Voyages/lessons/reflections,
AI conversations/messages, specialists/runs, support, and audit events.

## Validation

```bash
python -m pytest -q -p no:cacheprovider
python -m mypy --cache-dir=/dev/null app
node --check app/web/static/app.js
python -m pip check
python -m pip_audit -r requirements.lock --no-deps --disable-pip --strict \
  --cache-dir /tmp/cadre-pip-audit-cache
git diff --check
```

`requirements.lock` binds every production dependency to a reviewed Linux
x86_64 wheel hash. Production Python, PostgreSQL, and Caddy images are pinned
to verified multi-platform registry digests.

## Production operations

Production uses `ops/config/docker-compose.prod.yml`, a private PostgreSQL
network, an unprivileged read-only API container, and Caddy HTTPS. The public
product and intentionally public API paths are proxied to FastAPI; application
authorization protects private/user/admin/service resources. PostgreSQL,
Docker control, and the operations state API are not publicly exposed.

Read these before activation:

- `docs/HOSTINGER_OPERATIONS_RUNBOOK.md`
- `docs/RECOVERY.md`
- `SECURITY.md`
- `docs/ARCHITECTURE.md`
- `docs/EXTERNAL_DEPENDENCY_PACKET.md`

A clean repository or local health response is not evidence of a live VPS,
HTTPS, backups, restore capability, or remote deployment.
