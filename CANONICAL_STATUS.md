# CADRE Canonical Status

## Current authority

- System: CADRE M1 — Sovereign Core Foundation
- Version: 0.1.0
- Status: Current canonical core
- Promotion date: 2026-08-26
- Source package: `CADRE_M1_Sovereign_Core_Foundation_v0.1.0.zip`
- Verified source SHA-256: `24382898e4990a19f3d21fe9fc30cf6b4df0313dd0e8a20b19f3ac42674e387c`

The source package was designated as the new canonical CADRE core, superseding
the prior Next.js modular-monolith direction.

## Controlled installation changes

The source package was installed directly at the repository root. Its doctrine
seed content, registries, domain model, API contract, and milestone boundaries
remain unchanged. Installation hardening is limited to:

- binding the unauthenticated Docker API to `127.0.0.1`;
- excluding credentials, repository history, preserved data, and generated
  runtime state from the Docker build context;
- isolating the SQLite test database so repeated test runs are deterministic;
- verifying persisted project and command-brief linkage in the test;
- extending ignore rules for local secrets, generated output, and preserved
  pre-pivot runtime state.

## Preserved history and rollback

- Prior active branch: `feat/cadre-platform-foundation`
- Prior remote-aligned commit: `24bd3d4`
- Complete pre-pivot local preservation branch:
  `archive/pre-fastapi-m1-2026-08-26`
- Preservation commit: `156ce00`

The preservation branch contains the full pre-pivot tracked and untracked
non-secret state. Remote publication of that branch remains pending explicit
approval for the configured GitHub destination.

## Deferred by M1

LiteLLM/model routing, specialist assembly, LANSEIR orchestration, Mission
Control UI, Ready Dock, notifications, and VESSEL integration remain deferred.
They require separately authorized milestones and must not be reintroduced as a
parallel core.
