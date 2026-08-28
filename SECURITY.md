# Security Policy and Production Boundary

## Design controls

- No persistent agent root credentials
- Unix identity to role mapping
- Action and service allowlists; no arbitrary external command strings
- Root-owned controller, Compose policy, Caddy policy, and authorization files
- Write-ahead intent plus terminal, hash-chained operation receipts
- Constant-time ledger head checkpoint, invocation pacing, serialization, and fail-closed capacity
- Fixed canonical GitHub repository and protected `main` ancestry verification
- Root-generated exact-commit archive with size/count/path/link/device controls
- Compose-bound health probe that verifies the active release SHA
- Bearer service identity and role authorization on every non-health API route
- Bounded request bodies, schemas, pagination, every production container,
  subprocess output, release archives, backups, and restore streams
- Private application, internal, operations, and data networks
- No database, Docker socket, Mission Control admin surface, or AI admin endpoint exposed publicly
- Unprivileged read-only API container with dropped Linux capabilities
- Public HTTPS boundary limited to `/healthz` and the allowlisted LANSEIR product routes
- Explicit, verified, allowlisted administrator promotion; signup never grants admin
- Canonical-source SHA-256 enforcement before protected VESSEL content publication
- Bounded in-memory rate-limit state with normalized route categories
- Secrets excluded from Git, images, ordinary backups, state, and audit summaries
- Semantic secret preflight rejects placeholders, interpolation, weak/repeated
  credentials, duplicate identities, inconsistent database URLs, and unsafe file metadata

## Live Invictus acceptance

Repository checks cannot prove host security. Before production acceptance,
Invictus must verify on the VPS: SSH key policy, direct root-login policy,
firewall, Fail2ban or equivalent, externally listening ports, Docker
permissions, filesystem and secret permissions, HTTPS, public-route denial,
dependency results, logging, audit integrity, backup protection, and restore
testing.

Run the allowlisted host inspection with:

```bash
sudo /opt/lanseir/scripts/cadre-ops security-audit
sudo /opt/lanseir/scripts/cadre-ops audit-verify
```

Review the generated report; do not treat tool availability alone as a pass.

The local hash chain is not root-resistant evidence. Production acceptance also
requires a Griot-controlled external anchor for ledger head hashes and counts,
plus an encrypted off-server backup destination. The controller fails closed
at its local audit and backup limits; it does not silently delete evidence.

## Reporting

Do not place credentials, tokens, private keys, `.env` contents, database dumps,
or sensitive production logs in a GitHub issue. Preserve evidence in the
protected Griot/operations record and disclose only safe status metadata.
