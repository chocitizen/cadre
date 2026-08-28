# Universal Prompt Gateway Validation — 2026-08-28

## Verified locally

- Canonical LANSEIR foundation: PASS; nine registry records and eleven package
  files matched the promoted manifest.
- Gateway command semantics: PASS for `SIGNAL`, `NOW`, `GO`, `ADVANCE`, `ACT`,
  `ACTIVELY ADVANCE`, `DEPLOY`, `STATUS`, `+`, and `YOU KNOW WHAT TO DO`.
- Persistent execution state and privacy-aware receipts: PASS across independent
  database sessions and a stopped/restarted FastAPI process.
- Approval and lock behavior: PASS; unreferenced approval fails closed, Al
  cannot approve, Founder can approve an exact draft, and locked state requires
  Founder authority.
- Specialist routing and Al operator provisioning: PASS.
- Capability discovery: PASS; secret values are absent from adapter output and
  unavailable services remain blocked.
- Railway deploy failure contract: PASS; it returns the required capability,
  credential/permission class, affected service, exact action, and resume command.
- Python tests: PASS; 40 tests with one upstream Starlette deprecation warning.
- Static typing: PASS; 29 source files, zero issues.
- Dependency integrity: PASS; no broken requirements.
- Dependency vulnerability audit: PASS; no known vulnerabilities in the locked
  requirements at validation time.
- Python wheel build: PASS; the 0.4.0 wheel contains the gateway API, gateway
  service, execution-state bootstrap, and LANSEIR web shell/static assets; an
  isolated wheel install imported the 0.4.0 runtime successfully.
- Repository credential scan: PASS.
- Application import, Python compilation, JavaScript syntax, shell syntax, JSON
  policy syntax, and `git diff --check`: PASS.
- Runtime smoke: PASS on loopback port 8011; M3/version 0.4.0 health, authenticated
  `STATUS`, capability control plane, exact `DEPLOY` blocker, persisted revision,
  and receipt reload after process restart were verified.

## Proven capability boundary

- Git: local repository read, branching, commits, and tests are available. The
  application adapter does not claim remote mutation without a runtime service
  credential.
- Railway: blocked; its CLI, project binding, and runtime credential were not
  discovered. No staging deployment or URL is claimed.
- LiteLLM: CLI version 1.95.0 is present outside the release checkout, but the
  release remains on the local provider and no authenticated gateway route was
  proven.
- OpenRouter: not activated or live-validated; no provider credential was read.
- Hostinger: production operations remain disabled and no live host acceptance
  was performed.
- Docker/Compose: unavailable in the local validation environment. CI Compose
  rendering and image/build validation remain separate remote checks.

Repository validation is not Railway staging, provider readiness, protected-main
promotion, Hostinger deployment, or production acceptance.
