# CADRE Canonical Status

## Current authority

- System: CADRE M1 — Sovereign Core Foundation
- Canonical baseline version: 0.1.0
- Hostinger operations candidate: 0.2.0
- Status: Current canonical core with a locally validated operations proposal
- Promotion date: 2026-08-26
- Source package: `CADRE_M1_Sovereign_Core_Foundation_v0.1.0.zip`
- Verified source SHA-256: `24382898e4990a19f3d21fe9fc30cf6b4df0313dd0e8a20b19f3ac42674e387c`

The source package was designated as the new canonical CADRE core, superseding
the prior Next.js modular-monolith direction.

On 2026-08-28, the FULL SEND Hostinger operations authorization expanded the
canonical boundary without replacing the FastAPI core. LANSEIR remains the
sovereign parent; CADRE gains a constrained operations layer beneath it.

## Controlled installation changes

The source package was installed directly at the repository root. Its doctrine
seed content, registry domains, and milestone boundaries remain unchanged. The
API security contract now requires role tokens outside the public health route.
Installation hardening includes:

- binding the development Docker API to `127.0.0.1`;
- requiring role-scoped service authentication for every non-health API route;
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
- Hostinger operations checkpoint base: `8e36946`
- Hostinger operations rollback branch:
  `archive/pre-hostinger-ops-2026-08-28`

The preservation branch contains the full pre-pivot tracked and untracked
non-secret state. Remote publication of that branch remains pending explicit
approval for the configured GitHub destination.

## Deferred by M1

LiteLLM/model routing, specialist assembly, LANSEIR orchestration, Mission
Control UI, Ready Dock, notifications, and VESSEL integration remain deferred.
They require separately authorized milestones and must not be reintroduced as a
parallel core.

The role registry and internal Mission Control state model now exist, but ARC
model routing remains disabled until the separately validated AI service is
present. Repository implementation is not evidence of Hostinger installation
or production readiness; live acceptance remains governed by the runbook.

The 2026-08-28 operations proposal adds a canonical-Git deployment controller,
release-bound health, write-ahead auditing, bounded backups, and production
secret preflight. These changes remain proposed until the verified commit is
published to GitHub `main` and the live Hostinger acceptance sequence passes.
