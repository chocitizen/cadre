#!/usr/bin/env sh
set -eu

if command -v docker >/dev/null 2>&1 \
  && docker compose version >/dev/null 2>&1 \
  && docker compose ps --status running --services api 2>/dev/null | grep -qx api; then
  printf '\n[1/3] Container status\n'
  docker compose ps
  printf '\n[2/3] Health check\n'
  curl -fsS http://localhost:8000/api/v1/health
  printf '\n\n[3/3] Doctrine registry\n'
  docker compose exec -T api python -c 'import json, os, urllib.request; token=json.loads(os.environ["CADRE_API_TOKENS_JSON"])["mission_control"]; request=urllib.request.Request("http://127.0.0.1:8000/api/v1/doctrine", headers={"Authorization": f"Bearer {token}"}); print(urllib.request.urlopen(request, timeout=3).read().decode())'
  printf '\n\nLANSEIR / CADRE M2 validation PASS\n'
  exit 0
fi

python_bin="${CADRE_PYTHON:-.venv/bin/python}"
if [ ! -x "$python_bin" ]; then
  printf '%s\n' "Docker is unavailable and $python_bin was not found. Install the local development environment first." >&2
  exit 1
fi

printf '\n[1/4] Local test suite\n'
CADRE_DATABASE_URL='sqlite:///:memory:' PYTHONDONTWRITEBYTECODE=1 \
  "$python_bin" -m pytest -q -p no:cacheprovider
printf '\n[2/4] Type check\n'
"$python_bin" -m mypy --cache-dir=/dev/null app
printf '\n[3/4] Dependency integrity\n'
"$python_bin" -m pip check
printf '\n[4/4] Application import\n'
CADRE_DATABASE_URL='sqlite:///:memory:' PYTHONDONTWRITEBYTECODE=1 \
  "$python_bin" -c 'from app.main import app; assert app.title'
printf '\nLANSEIR / CADRE M2 local validation PASS\n'
