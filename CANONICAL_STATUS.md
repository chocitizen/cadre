# LANSEIR / CADRE Canonical Status

## Current authority

- Parent platform: LANSEIR
- Internal operating system: CADRE
- Repository milestone: M2 product spine
- Version: 0.3.0
- State: locally validated release candidate; production activation unverified
- Base architecture: canonical FastAPI M1 at `fb2d768`
- Preserved rollback: `archive/pre-fastapi-m1-2026-08-26` / `156ce00`
- Operations base: `8e36946`; pre-operations rollback branch remains preserved

M2 extends the canonical FastAPI architecture in place. It does not restore
the superseded Next.js/LiteLLM core or create a competing application.

## Authoritative implementation

The repository now contains one coherent product/runtime boundary:

- FastAPI owns public pages, user APIs, service APIs, migrations, and static UI.
- PostgreSQL is the production system of record; SQLite is supported for local
  validation.
- Opaque server-side sessions and CSRF protect browser state.
- Service tokens remain separate from user identity and are domain-scoped.
- CADRE specialists are functional role definitions. Runs reflect actual
  queued/running/completed/failed state; no continuously running agents are
  implied.
- The local Reflection Guide is the default. Paid/external model calls remain
  opt-in and server-side.
- Hostinger operations remain governed by the root-owned `cadre-ops` boundary.

## Protected source boundary

VESSEL metadata and the product mechanics are present. No manuscript chapter
or audiobook source has been approximated, regenerated, or promoted. The
repository seed stays `draft` until the exact authorized Sirrah Publishing
source is ingested and an administrator explicitly changes the content state.

## Production boundary

Local tests, type checks, browser E2E, and dependency checks have passed.
Docker is absent on this host, and no authenticated Hostinger session was
available. Therefore container build, deployed PostgreSQL migration, Caddy
validation, HTTPS, DNS, live backup/restore, CI at the new commit, and remote
health remain unverified external gates.
