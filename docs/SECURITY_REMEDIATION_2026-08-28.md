# CADRE Security Remediation — 2026-08-28

Status: repository controls locally remediated; live Hostinger acceptance blocked by authentication.

## Review record

- Standard repository scan ID: `cb5e0983-fdb7-42af-a6ff-fff67fce95d9`
- Coverage: 50 in-scope files, complete
- Initial candidates: 8 (5 medium, 3 low)
- Follow-up: one independent post-patch bypass review, followed by targeted remediation and regression tests

## Protected invariants and local outcome

| Invariant | Local outcome |
| --- | --- |
| Private API callers authenticate as one unique role and writes remain limited to Mission Control/Al | Enforced; duplicate, unknown, short, weak, or interpolated token policy fails closed |
| Requests and records cannot grow without policy bounds | Enforced at ASGI body, field, aggregate JSON, depth, list, and pagination boundaries |
| Deployment input is an exact canonical Git commit on GitHub `main` | Enforced by root-owned repository policy, exact SHA resolution, ancestry check, and root-generated archive |
| Release extraction cannot escape staging or consume unbounded members/files/memory | Enforced with streaming member inspection and compressed, expanded, member, and per-file ceilings |
| Health evidence belongs to the active Compose API and expected release | Enforced through Compose service status, in-container health request, and release-SHA comparison |
| Failed activation never claims an unverified rollback or current release | Enforced for ordinary failures, timeouts, and subprocess errors; first-deploy failure clears the pointer only after candidate shutdown |
| Privileged operations are serializable and attributable | Enforced with a host operation lock, typed allowlists, durable intent, terminal receipt, actor/role, result, and exit status |
| Audit use cannot grow request-time work or storage without bound | Enforced with a constant-time head checkpoint and a 64 MiB fail-closed ceiling |
| Audit intent survives a completed append as far as filesystem semantics permit | Ledger and head file data are synced; the containing directory is synced after atomic replacement |
| Production secrets are semantic, unique, and literal | Placeholder, repeated/weak, duplicate, interpolated, malformed host/email, unexpected DB port/query/fragment, URL mismatch, owner, and mode checks fail closed |
| Backup/restore work remains bounded | Database streams use fixed blocks, dump/free-space ceilings, partial-set accounting, local count/frequency limits, checksum verification, and isolated restore testing |
| Every production container has CPU, memory, and PID bounds | PostgreSQL, API, and proxy all declare limits; the database remains internal and unexposed |
| Subprocess output cannot exhaust controller memory | Output is spooled to temporary files and only a bounded tail is returned |

## Remaining live acceptance

Repository evidence cannot establish the VPS firewall, SSH/root-login policy,
Fail2ban, listening ports, Docker group membership, deployed filesystem
ownership, HTTPS certificate/routing, live backup/restore, or external audit and
backup custody. These remain mandatory Invictus/Griot/Porter gates in the
Hostinger runbook. No production security completion is claimed.
