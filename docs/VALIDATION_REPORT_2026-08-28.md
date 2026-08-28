# CADRE Hostinger Operations Validation — 2026-08-28

Status: local candidate PASS; GitHub publication and Hostinger production acceptance BLOCKED.

## Verified locally

- Clean Python 3.12 environment resolved the declared development dependencies, including `pytest 9.0.3+`.
- Test suite: 25 passed.
- Mypy type check: no issues in 17 application source files.
- Dependency integrity: `pip check` passed.
- Dependency audit: no known vulnerabilities in the clean resolved environment; the unpublished local `cadre-core` package was source-reviewed separately.
- Python compilation passed for `app`, `ops`, and `tests`.
- Shell syntax passed for the installer, wrappers, and validation script.
- JSON policy parsing passed for actors, roles, services, limits, and repository policy.
- YAML parsing passed for development Compose, production Compose, and GitHub Actions.
- Wheel build passed for `cadre-core 0.2.0`.
- `git diff --check` passed.
- High-signal credential/private-key pattern scan returned no matches.
- Repository security scan completed across 50 files; the remediation record is in `SECURITY_REMEDIATION_2026-08-28.md`.

## Explicitly unverified

- Docker/Compose build and runtime: Docker is not available on this Mac environment.
- GitHub Actions: the candidate is not on GitHub `main`, so CI has not run for it.
- Hostinger install, systemd timers, Caddy/HTTPS, firewall, SSH, Fail2ban, public-port exposure, live health, governed operations, backup, restore test, restart, and rollback: no authenticated VPS session was available.
- Encrypted off-server backup destination and external Griot audit-head anchor: provider/operator decisions remain open.

The acceptance gate remains closed until the runbook's complete live sequence
passes. Local implementation or repository tests are not production evidence.
