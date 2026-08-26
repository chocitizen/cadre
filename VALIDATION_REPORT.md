# CADRE M1 Validation Report

Date: 2026-08-26
Scope: Canonical FastAPI M1 root installation

## Result

Local executable validation: **PASS**

The canonical core builds and runs locally with an isolated Python 3.12
environment and SQLite validation database. Docker Compose execution remains an
external gate because Docker is not installed on this Mac.

## Verified evidence

- Source ZIP SHA-256 matched
  `24382898e4990a19f3d21fe9fc30cf6b4df0313dd0e8a20b19f3ac42674e387c`.
- All unchanged application, packaging, environment-template, and validation
  files matched the verified source package byte-for-byte.
- Controlled installation changes were limited to `.gitignore`, `.dockerignore`,
  `README.md`, `MANIFEST.md`, `docker-compose.yml`, `tests/test_core.py`, and
  the canonical provenance and validation records.
- The project wheel built successfully from `pyproject.toml` under Python
  3.12.13.
- `pip check` reported no broken requirements.
- Pytest passed twice consecutively: 1 test passed on each run.
- The test covers root metadata, Swagger availability, health, doctrine seed
  loading, project creation, command-brief creation, persistence, and linkage.
- Python AST parsing passed for all 16 application and test source files.
- `docker-compose.yml` parsed successfully and binds the unauthenticated API to
  `127.0.0.1:8000` only.
- `scripts/validate.sh` passed shell syntax validation.
- A live Uvicorn process bound to `127.0.0.1` returned:
  - HTTP 200 from `/api/v1/health`;
  - seven doctrine entries, including `sovereignty`;
  - HTTP 200 from `/docs`;
  - HTTP 200 from `/openapi.json`.
- Git whitespace validation passed.
- Secret-pattern screening found no credential value. The committed
  `change_me` database-password placeholder remains intentionally present in
  the example configuration and must be replaced only in ignored `.env` and
  the deployment configuration before Docker startup.
- `.env`, `.env.local`, preserved backups, prior generated state, repository
  history, databases, and ZIP files are excluded from the Docker build context.

## Non-blocking warning

The current FastAPI/Starlette test client emits one upstream deprecation warning
about the HTTP test-client package. It does not affect execution or test results
but should be revisited during dependency locking or the next maintenance
milestone.

## Remaining external gate

The PostgreSQL Docker stack and `./scripts/validate.sh` have not been executed
on this host because Docker and Docker Compose are not installed. Run that
validation on the approved private VPS or another authorized Docker host after
setting a strong matching database password. Do not expose port 8000 publicly.
