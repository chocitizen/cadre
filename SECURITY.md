# Security Policy and Production Boundary

## Public surface

Production intentionally publishes the LANSEIR product, public identity entry
points, health, legal pages, and support intake through Caddy HTTPS. FastAPI
Swagger, ReDoc, and OpenAPI schema routes are disabled in production.

Private user routes require an opaque server-side session. Mutations require a
matching CSRF cookie/header. User-owned queries enforce owner IDs server-side.
Admin routes enforce the database role; browser presentation is not an access
control. Service registries use a separate bearer-token boundary.

PostgreSQL, Docker, host operations, and the operations-state service API have
no public host port. Caddy and ASGI enforce body bounds; Uvicorn has explicit
concurrency/keep-alive limits. Authentication and AI routes have per-process
request-rate ceilings; a distributed limiter is required if the API is scaled
to multiple replicas.

## Implemented controls

- Salted scrypt password hashes; raw passwords are never logged
- HttpOnly `Secure` production session cookies, SameSite Lax, token hashes at rest
- CSRF validation on authenticated mutations
- Domain-scoped service roles and constant-time bearer-token comparison
- Owner-scoped private journals, notes, bookmarks, progress, reflections, and AI context
- Bounded bodies, fields, JSON depth, pagination, AI context, output, archives,
  backups, subprocess output, containers, and audit storage
- Request correlation IDs, generic production errors, CSP, HSTS, frame denial,
  content-type, referrer, and permissions policy
- HTTPS/loopback-only AI provider URL policy; provider keys remain server-side
- Hash-locked production Python wheels and digest-pinned official images
- Root-owned typed operations; exact canonical Git ancestry; bounded extraction
- Write-ahead intent and terminal hash-chain receipts for mutations and
  protected logs; protected output is suppressed if terminal audit fails
- Private application/data/operations networks and unprivileged read-only API
- Secret placeholders, weak/repeated credentials, interpolation, ownership,
  file mode, URL consistency, and operator-email checks fail closed

## Security review

The exact pre-M2 revision `6a2c9936e8146d3e069358baf6aeea09ec7cc7ce`
received a complete repository-wide static review. It reported six validated
findings: four medium and two low. M2 remediates their root controls:

1. production dependency resolution now uses `requirements.lock` and
   `--require-hashes`;
2. Python/PostgreSQL/Caddy images are digest pinned;
3. public request buffering has method, byte, concurrent-read, and time bounds;
4. low-privilege services no longer receive global registry/state reads;
5. protected logs fail closed on audit receipt failure;
6. schema/documentation routes are disabled in production.

The report is preserved outside the release tree as a validation artifact.
Post-change regression includes 29 tests, mypy, browser E2E, dependency lock
verification, and `pip-audit` with no known production dependency vulnerabilities.

## Live acceptance

Repository checks cannot prove VPS SSH/root policy, firewall, Fail2ban,
listeners, Docker permissions, deployed ownership, TLS, backup custody, or
restore results. Before production acceptance, Invictus must run:

```bash
sudo /opt/lanseir/scripts/cadre-ops security-audit
sudo /opt/lanseir/scripts/cadre-ops audit-verify
```

The local ledger is not root-resistant evidence. Production also requires a
Griot-controlled external audit-head anchor and encrypted off-server backups.

Do not place credentials, tokens, private keys, `.env` content, dumps, private
journal text, or protected logs in GitHub issues. Report only safe metadata.
