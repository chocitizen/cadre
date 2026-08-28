# LANSEIR / CADRE Recovery

## Functional recovery and browser FIX

Recovery applies to every mission action, not only deployment. Failed, blocked,
stalled, and verification-failed missions expose FIX in Mission Control. A
deterministic failure automatically creates and dispatches an Al recovery
mission containing the original failure evidence and root-cause context.

Al must record both diagnosis and repair evidence. Griot or Mission Control must
record passed verification before the original mission can resume. Resumption
increments the retry counter and cannot exceed the mission retry ceiling.
Authorization, policy, and unresolved dependency failures remain blocked for a
real authority or dependency change; FIX does not bypass controls.

## Release rollback

`cadre-ops deploy` preserves the former current release as `previous` before
activation. If build, start, or health validation fails, the controller restores
and health-verifies the former release automatically. It reports `ROLLED_BACK`
only after verification; otherwise it reports `RECOVERY_REQUIRED`. A
human-authorized rollback uses:

```bash
sudo /opt/lanseir/scripts/cadre-ops rollback
```

Rollback never accepts an arbitrary path. It uses only the root-managed
`previous` pointer and health-checks the result. If the rollback candidate fails,
the controller restores and verifies the release that was current when rollback
began. An unverified restoration is never represented as successful recovery.
If the first deployment fails and there is no former release, the controller
stops the candidate Compose project and removes the unverified `current`
pointer. If shutdown cannot be verified, state becomes `RECOVERY_REQUIRED`.

## Backup scope

Porter backs up PostgreSQL logical data, CADRE/Mission Control state, operations
audit records, and root-owned operations policy. The populated secrets directory
is deliberately excluded. Each backup has a manifest containing the current
release and SHA-256 values.

Backup and restore database streams are bounded in memory. The controller
serializes privileged operations, enforces a minimum backup interval, local-set
ceiling, database-dump ceiling, and free-space reserve, and fails closed when
those limits are reached. Interrupted partial sets count toward both the
frequency and local-set limits. No recovery set is deleted until an
independently verified off-server copy and authorized retention decision exists.

## Verification and restore test

```bash
sudo /opt/lanseir/scripts/cadre-ops backup-verify
sudo /opt/lanseir/scripts/cadre-ops restore-test
```

The restore test creates an isolated temporary PostgreSQL database, restores the
latest logical dump with stop-on-error enabled, verifies a database query, and
drops the temporary database. It does not replace production data.

## Off-server recovery dependency

An encrypted, access-controlled off-server copy is required before production
acceptance. The repository intentionally does not choose or embed a storage
provider. Record the selected destination, retention, encryption ownership,
restore operator, and last successful recovery exercise in the protected
operations record.

## Emergency recovery

Root remains the emergency authority. Preserve `/opt/lanseir/releases`,
`/opt/lanseir/backups`, `/opt/lanseir/logs/audit`, and the Docker volumes before
manual repair. Never delete a failed release or audit record until its incident
receipt and replacement evidence are preserved.
