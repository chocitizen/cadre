# CADRE — Milestone 1: Sovereign Core Foundation

This package establishes the first executable CADRE kernel: persistent doctrine, projects, command briefs, and system health.

## Install

From the CADRE project root after extracting this package:

```bash
cp .env.example .env
```

Change the two occurrences of `change_me` in `.env` and `docker-compose.yml` to the same strong database password.

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

## M1 API

- `GET /api/v1/health`
- `GET /api/v1/doctrine`
- `POST /api/v1/doctrine`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/command-briefs`
- `POST /api/v1/command-briefs`

## Security boundary

M1 intentionally does not expose this service as a production public API with
authentication. Docker Compose binds port 8000 to `127.0.0.1` so it remains
private to the host until the identity/authentication milestone and an approved
HTTPS boundary are installed. Do not place this directly on the public internet
as-is.
