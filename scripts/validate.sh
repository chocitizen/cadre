#!/usr/bin/env sh
set -eu
printf '\n[1/3] Container status\n'
docker compose ps
printf '\n[2/3] Health check\n'
curl -fsS http://localhost:8000/api/v1/health
printf '\n\n[3/3] Doctrine registry\n'
curl -fsS http://localhost:8000/api/v1/doctrine
printf '\n\nCADRE M1 validation PASS\n'
