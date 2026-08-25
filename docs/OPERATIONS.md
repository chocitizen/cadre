# Operations

## Local operating mode

CADRE currently runs as one local Next.js process with local PostgreSQL-compatible storage. No process manager, reverse proxy, container runtime, remote host, or production monitoring service is configured.

## First-time bootstrap

```bash
npm ci
npm run verify:env
npm run db:migrate
npm run db:seed
npm run owner:create
```

Run the interactive owner bootstrap in a private terminal. Do not include credentials in command arguments, redirected files, screenshots, logs, or chat.

## Start and stop

Development:

```bash
npm run dev
```

Validated local production build:

```bash
npm run build
npm run start
```

Stop the foreground process with `Ctrl-C`. Do not terminate the host or delete runtime data to stop the application.

## Health and verification

Use the application health endpoint for process liveness. Health must not return secrets, full environment variables, private paths, provider credentials, or private message content.

Run:

```bash
npm run verify:env
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

The live OpenAI check is explicit and separate:

```bash
npm run test:openai
```

Record pass/fail status without logging provider credentials or full sensitive responses.

## Routine operation

- Review failed and approval-blocked jobs.
- Confirm Ready Dock rows open the exact persisted artifact.
- Review active sessions and revoke unexpected access.
- Review audit events for administrative and approval actions.
- Check data volume, backup freshness, and restore evidence.
- Run dependency and application validation before release.
- Keep the single next executable action visible when work pauses.

## Incident response

1. Contain exposure or stop the affected process.
2. Preserve logs and the last known-good state without copying secrets into reports.
3. Identify the exact affected data, account, workspace, or release.
4. Revoke or rotate compromised credentials through the authorized provider interface.
5. Restore or roll back only the affected component.
6. Retest the failed path and dependent paths.
7. Record evidence, remaining risk, owner, and next action.

Never bypass authentication, disable security controls, destroy evidence, or silently rewrite canonical state to resolve an incident.

## Status language

Use Created, Functional, Validated, Approved, and Production Ready precisely. A successful build does not establish authentication, persistence, provider, backup, restore, or deployment readiness unless each was tested.
