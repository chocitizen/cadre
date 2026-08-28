# LANSEIR Autonomous Platform Validation — 2026-08-28

## Verified locally

- Canonical foundation integrity: PASS; 9 registry records and 11 package files
  matched the promoted manifest.
- Repository credential-pattern scan: PASS; populated `.env.local` remained
  ignored and was not read into logs or copied into the promotion set.
- Python tests: PASS; 33 tests, 1 upstream Starlette deprecation warning.
- Static typing: PASS; 23 source files, zero issues.
- Dependency integrity: PASS; no broken requirements.
- Dependency vulnerability audit: PASS; no known vulnerabilities in the locked
  runtime requirements at validation time.
- JavaScript syntax: PASS.
- Operations shell and JSON policy syntax: PASS.
- Fresh runtime smoke test on loopback port 8010: public health 200, LANSEIR
  product shell 200, unauthenticated Mission Control 401, authorized Mission
  Control 200, expected mission/evidence/artifact state fields present.
- `git diff --check`: PASS.

## Implemented controls

- Evidence-gated mission completion and dependency-ready dispatch.
- Status-only chatter rejected as progress evidence.
- Deterministic failure creates and dispatches an Al recovery mission.
- FIX available through internal API and the verified-admin dashboard.
- Porter artifact registration, archive, cleanup, and only-copy protection.
- Signup cannot self-promote to admin; Mission Control may promote only a
  verified email on the configured allowlist.
- VESSEL chapters require approved source provenance and exact SHA-256 match.
- Sessions, CSRF, reset-token invalidation, account export/deletion, normalized
  bounded rate limits, and fail-closed environment names.
- Production proxy allowlists approved product routes and denies internal,
  admin, doctrine, registry, Mission Control, and content-source routes.

## External gates — not claimed

- GitHub: the repository named exactly `lanseir` was not visible to the current
  authenticated `chocitizen` account; remote connection, push, branch
  protection, and GitHub-hosted CI are blocked. The existing `cadre` origin is
  preserved and has not been repointed.
- Hostinger: no verified host access or SSH host configuration was available;
  installation, DNS, HTTPS, firewall, deployment, backup, and restore acceptance
  were not run.
- Containers/proxy: Docker and Caddy executables were unavailable locally;
  Compose rendering, image build, container health, and Caddy config adaptation
  remain unverified outside repository tests.
- LiteLLM: local CLI version 1.95.0 exists, but no LiteLLM listener was active.
- OpenRouter: no OpenRouter credential or verified provider route was found.
  The local zero-provider-cost Guide remains the enabled default.
- Identity email delivery: no delivery adapter or verified provider is active,
  so verification and recovery responses accurately report delivery as pending.

Repository validation is not production acceptance. Complete the external gates
in `docs/DEPLOYMENT_SOP.md` and `docs/HOSTINGER_OPERATIONS_RUNBOOK.md` before
marking the platform live.
