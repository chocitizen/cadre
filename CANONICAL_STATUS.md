# LANSEIR Canonical Status

## Current authority

- System: LANSEIR sovereign platform with CADRE internal execution
- Canonical baseline version: 0.1.0
- Hostinger operations candidate: 0.2.0
- Autonomous platform candidate: 0.3.0
- Status: Locally validated candidate; protected-main review and production acceptance pending
- Promotion date: 2026-08-26
- Source package: `CADRE_M1_Sovereign_Core_Foundation_v0.1.0.zip`
- Verified source SHA-256: `24382898e4990a19f3d21fe9fc30cf6b4df0313dd0e8a20b19f3ac42674e387c`

The source package was designated as the new canonical CADRE core, superseding
the prior Next.js modular-monolith direction.

On 2026-08-28, FULL SEND authorization expanded the canonical boundary without
replacing the FastAPI core. The candidate adds the LANSEIR product shell,
evidence-gated mission execution, deterministic recovery/FIX, canonical-content
provenance, and Porter lifecycle records. The verified foundation package is
preserved byte-for-byte under `provenance/` and enforced by
`scripts/validate_foundation_sync.py`.

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

## External gates

The configured private `chocitizen/cadre` remote is preserved; it was not
silently repointed. Candidate branch `feat/lanseir-m2-completion` is published,
and protected pull request #1 is open. GitHub
requires an independent approving review before promotion to `main`. Hostinger
deployment, DNS/HTTPS acceptance, off-server backup, and live restore evidence
remain blocked until host access and production inputs are verified.

ARC model routing remains disabled until a separately validated LiteLLM service
and provider credentials are present. Repository implementation is not evidence
of live Hostinger installation or production readiness.

The 2026-08-28 operations proposal adds a canonical-Git deployment controller,
release-bound health, write-ahead auditing, bounded backups, and production
secret preflight. These changes remain proposed until the protected pull
request is approved and merged to GitHub `main`, then the live Hostinger
acceptance sequence passes.
