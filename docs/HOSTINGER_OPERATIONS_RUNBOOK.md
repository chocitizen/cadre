# LANSEIR / CADRE Hostinger Operations Runbook

## Authority and boundary

LANSEIR is the sovereign parent platform. CADRE is the governed execution
layer. Root remains emergency/administrative authority; no agent receives a
persistent root credential. Operational elevation is available only through
the root-owned `/opt/lanseir/scripts/cadre-ops` controller.

The production application API, PostgreSQL, Mission Control state, operations
controller, and Docker control remain private. Caddy exposes only the HTTPS
`/healthz` route.

## Required host baseline

- Ubuntu or Debian-compatible Hostinger VPS with systemd
- Docker Engine with Compose v2
- `sudo`, `visudo`, `ufw`, and Fail2ban or an approved equivalent
- A DNS name already pointed at the VPS
- SSH key access for the human administrator
- A distinct deployment public key for `lanseir-deploy`

## Canonical filesystem

```text
/opt/lanseir/
├── apps/cadre/{current,previous}
├── cadre/{mission-control,agents,orchestration,jobs,state,policies}
├── infrastructure/{proxy,docker,monitoring,security}
├── releases/<full-git-sha>
├── shared
├── logs/{audit,security}
├── backups
├── scripts
├── libexec
└── secrets
```

The installer creates this structure, installs root-owned policy and controller
files, creates non-root role identities, installs narrow sudo authorization,
and registers Sentinel and Porter systemd timers.

## Controlled installation

From an already validated, immutable repository checkout:

```bash
sudo bash ops/install.sh
```

Then populate `/opt/lanseir/secrets/cadre.env` directly on the server. It must
remain owned by `root:root`, mode `0600`, and must never be copied into Git.
Required names are documented in `ops/config/cadre.env.example`; values are not
stored in this repository. Use unique 32-plus-character tokens for Mission
Control, Al, Invictus, Porter, Griot, and Sentinel. The controller rejects
template values, weak/repeated credentials, interpolation syntax, unexpected
database ports/options, duplicate role tokens, and unsafe file metadata before
any Compose-backed operation.

Install the deployment public key in
`/home/lanseir-deploy/.ssh/authorized_keys`. Keep password authentication and
direct root login disabled after verifying a separate administrative recovery
session.

## Governed operations

All privileged actions use this shape:

```bash
sudo /opt/lanseir/scripts/cadre-ops ACTION [APPROVED_TARGET]
```

The caller is derived from the Unix/sudo identity. `actors.json`, `roles.json`,
and `services.json` are root-owned. Unknown actors, actions, service names, and
disabled services fail closed and are audited.

Deploy accepts only a lowercase 40-character Git commit SHA. The root controller
fetches the fixed repository in `repository.json`, requires the commit to be an
ancestor of canonical GitHub `main`, generates the release archive from that
exact commit, enforces extraction size/count/path/type limits, installs an
immutable root-owned release, and atomically moves the `current` pointer. No
deployment identity can supply an archive or checksum. Health is checked from
inside the fixed Compose API service and must report the expected release SHA.
Fallback is reported as `ROLLED_BACK` only after the former release is running
and passes the same identity-bound health check; otherwise state becomes
`RECOVERY_REQUIRED`. Timeouts and subprocess launch failures are converted into
bounded failure results and enter the same recovery path.

## Role map

- Mission Control: global state and all approved dispatch operations
- Al: build, test, deploy, validate, API/proxy restart and logs
- ARC: AI health/restart only; currently blocked because LiteLLM is disabled
- Invictus: security, permissions, exposure, audit verification
- Porter: backup, verify, isolated restore test, storage/maintenance status
- Griot: read-only release, validation, state, and audit verification
- Sentinel: deterministic health and resource observation

## Mission Control state

The controller writes a sanitized state snapshot at
`/opt/lanseir/cadre/state/mission-control.json`. The private API reads that file
at `/api/v1/operations/state`. It includes system, deployment, release, role,
assignment, and activity state but never secret values.

## Production acceptance sequence

1. Verify the source commit and recovery branch.
2. Run repository CI and confirm all checks pass.
3. Install or update the root-owned operations policy through the administrative session.
4. Confirm the exact commit exists on canonical GitHub `main`.
5. Invoke `deploy <commit-sha>` as the mapped deployment identity; the root controller fetches it independently.
6. Run `validate`, `status`, `system-health`, and `audit-verify`.
7. Confirm HTTPS `/healthz` externally and confirm all other public paths return `404`.
8. Run `backup`, `backup-verify`, and `restore-test`.
9. Run `security-audit` and independently inspect externally reachable ports.
10. Confirm the current release, last known-good release, timer schedule, and recovery records.
11. Confirm encrypted off-server backup evidence and an independent Griot audit-head anchor.

Do not mark production complete when any live check above is unavailable.
