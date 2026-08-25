# Backup, Restore, and Rollback

## Current state

The local Git repository, ignored runtime data, and `.env.local` are separate recovery domains. At reconnaissance there was no commit, remote repository, independent application-data backup, or tested production restore.

Git history is not a database backup. iCloud synchronization is not proof of a consistent Git or database backup. A secret file must not be placed in the repository merely to make recovery convenient.

## What must be protected

- application source and migrations;
- operational database;
- artifact payloads;
- audit evidence;
- configuration names and safe templates;
- secure external credential-recovery records;
- verified repository and deployment metadata.

## Local data backup

Before backing up the embedded local store:

1. Stop the application cleanly.
2. Confirm no migration or write process is active.
3. Copy the configured `CADRE_DB_PATH` directory to a timestamped, encrypted, access-controlled location outside the repository.
4. Record the application commit, schema/migration state, checksum or integrity evidence, date, custodian, and restore-test date.
5. Restart only after the copy completes.

Do not copy `.env.local` into ordinary backups. Preserve provider and account recovery through a separate authorized secret-management process.

## Local restore test

1. Preserve the current failed or suspect state as evidence.
2. Restore the backup into a new explicit directory.
3. Point `CADRE_DB_PATH` to the restored copy without overwriting the original.
4. Start the application locally.
5. Verify authentication, workspace access, conversation persistence, Ready Dock, artifact open, and audit continuity.
6. Record failures, corrections, and the tested recovery point.
7. Promote the restored copy only after validation and authorization.

## PostgreSQL target

Before a production PostgreSQL deployment, define and test:

- encrypted backup mechanism and retention;
- point-in-time recovery requirements;
- `pg_dump`/restore or provider-native export path;
- backup access and separation of duties;
- migration rollback strategy;
- artifact-store consistency;
- recovery-time and recovery-point objectives.

No production database or backup mechanism is currently verified.

## Code rollback

After the repository has validated commits or tags:

1. identify the deployed commit and last known-good commit;
2. preserve uncommitted evidence;
3. create a rollback branch or deploy the known-good immutable release;
4. avoid force-pushing or rewriting history;
5. verify schema compatibility before changing application code;
6. run regression, persistence, and security checks;
7. record the rollback decision and next correction.

Do not use destructive reset commands as a routine rollback mechanism.

## Recovery gate

Recovery is validated only when data, relationships, authority metadata, artifacts, and operability are demonstrated—not when files merely exist.
