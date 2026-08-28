# LANSEIR / CADRE M2 Validation Report

Date: 2026-08-28
Scope: local M2 release candidate

## Result

Local application validation: **PASS**
Production deployment validation: **NOT RUN — external Hostinger/Docker gate**

## Exact local evidence

- Pytest: **29 passed**, one upstream TestClient deprecation warning
- Mypy: **Success; no issues in 22 source files**
- JavaScript syntax: `node --check` passed
- Python compile: passed using an isolated temporary bytecode cache
- Dependency integrity: `pip check` reported no broken requirements
- Production dependency audit: `pip-audit` reported no known vulnerabilities
- Linux CPython 3.12 production lock: all 24 pinned wheels re-downloaded and
  verified with `--require-hashes`
- Shell syntax: installer and operations wrappers passed
- JSON policy: actors, roles, services, limits, and repository files parsed
- Git whitespace: `git diff --check` passed
- Initial exact-revision security scan: completed, six findings; root controls
  remediated and regression covered

## Browser E2E

The product ran under Uvicorn on loopback and was exercised through the in-app
browser as a real user:

1. public entry rendered with CSP and no horizontal overflow;
2. account creation established an admin session;
3. authenticated Here/Library shell loaded;
4. Captain's Log entry created, edited, and persisted;
5. Voyage enrolled, first lesson completed, and next lesson unlocked;
6. local Reflection Guide produced and persisted a response;
7. Mission Control showed real users, Voyage/run state, routing, and specialists;
8. sign-out denied private access; sign-in restored journal and Voyage state;
9. Privacy, Support, and server-backed 404 routes rendered;
10. responsive checks passed at widths 375, 430, 768, 1280, and 1440 with no
    horizontal overflow;
11. a fresh final load produced zero console warnings/errors.

The browser database and credentials were temporary local validation fixtures,
not production data.

## Not verified here

- Docker/Compose production build: Docker is absent on this Mac
- Caddy config execution and TLS issuance
- GitHub Actions at the new commit
- Hostinger deploy, public hostname, DNS/HTTPS, PostgreSQL migration, health,
  logs, backup, restore, restart, rollback, external audit anchor, or off-server custody
- Transactional email delivery, authorized VESSEL source ingestion, paid AI,
  payments, or formal legal approval

No unrun item is reported as passing.
