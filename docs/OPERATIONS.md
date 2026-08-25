# Operations

## Local operating mode

CADRE Core runs as one local Next.js process with local PostgreSQL-compatible storage. Live AI adds a separately managed LiteLLM 1.95.0 process bound to `127.0.0.1:4000`; deterministic application validation does not require that external-inference path. No process manager, reverse proxy, container runtime, remote host, or production monitoring service is configured.

## First-time bootstrap

```bash
npm ci
npm run ai:gateway:install
npm run verify:env
npm run db:migrate
npm run db:seed
npm run owner:create
```

Run the interactive owner bootstrap in a private terminal. Do not include credentials in command arguments, redirected files, screenshots, logs, or chat.

The LiteLLM installer requires Python 3.10 through 3.14. On Intel macOS, the pinned package may build from source and also needs the Xcode Command Line Tools; its build backend may bootstrap Rust into the user's cache. Place gateway and provider secrets only in `.env.local`. Phase 1 requires `OPENROUTER_API_KEY` for external inference; it does not require `OPENAI_API_KEY` or OpenAI billing.

## AI configuration

| Variable                     | Purpose                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------ |
| `CADRE_AI_PROVIDER`          | CADRE adapter selection; Phase 1 is `litellm`                                  |
| `CADRE_AI_GATEWAY_URL`       | Server-only LiteLLM origin; local default is `http://127.0.0.1:4000`           |
| `CADRE_AI_GATEWAY_API_KEY`   | Shared gateway credential; optional on loopback, required for a remote gateway |
| `CADRE_AI_MODEL`             | CADRE-facing model alias; Phase 1 is `cadre-free`                              |
| `CADRE_AI_TIMEOUT_MS`        | Bounded CADRE-to-gateway request timeout                                       |
| `OPENROUTER_API_KEY`         | Server-only OpenRouter credential; required only for the active external lane  |
| `OPENROUTER_API_BASE`        | OpenRouter API origin                                                          |
| `CADRE_OPENROUTER_MODEL`     | LiteLLM provider model; Phase 1 is `openrouter/openrouter/free`                |
| `OR_SITE_URL`, `OR_APP_NAME` | Non-secret OpenRouter application attribution                                  |
| `CADRE_LOCAL_MODEL`          | Optional future local/self-hosted model identifier                             |
| `CADRE_LOCAL_API_BASE`       | Optional future local/self-hosted endpoint                                     |
| `CADRE_LOCAL_API_KEY`        | Optional future local gateway credential                                       |
| `CADRE_PREMIUM_MODEL`        | Optional future premium/direct model identifier                                |
| `CADRE_PREMIUM_API_KEY`      | Optional future premium/direct credential                                      |
| `OPENAI_API_KEY`             | Optional future direct OpenAI lane; unused by default                          |
| `ANTHROPIC_API_KEY`          | Optional future direct Anthropic lane; unused by default                       |
| `GEMINI_API_KEY`             | Optional future direct Google Gemini lane; unused by default                   |

Use the safe defaults and empty placeholders in `.env.example`; put real credentials only in `.env.local`. Never print environment values or expose any credential through a `NEXT_PUBLIC_` variable.

## Start and stop

Development:

```bash
npm run dev
```

Live AI gateway, in a separate private terminal:

```bash
npm run ai:gateway:start
```

This loads `config/litellm.yaml`, binds LiteLLM to loopback, and exposes the `cadre-free` alias. The launcher forwards only active OpenRouter and necessary host/TLS variables; inactive direct-provider keys are withheld. Do not expose port 4000 publicly. Local/self-hosted and premium/direct-provider lanes remain inactive until separately configured and approved; premium fallback is disabled by default.

Validated local production build:

```bash
npm run build
npm run start
```

Stop the foreground process with `Ctrl-C`. Do not terminate the host or delete runtime data to stop the application.

## Health and verification

Keep the checks distinct:

- `/api/health/live` establishes only that the CADRE process is live.
- `/api/health/ready` establishes CADRE application and database readiness.
- `npm run test:ai:live` sends a minimal server-side completion through the configured LiteLLM gateway and model alias.

Application health must not depend on an external model call and must not return secrets, full environment variables, private paths, provider credentials, prompts, responses, or private message content.

Run:

```bash
npm run verify:env
npm run verify:secrets
npm run format:check
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

The live AI gateway check is explicit and separate:

```bash
npm run test:ai:live
```

It calls the configured `CADRE_AI_GATEWAY_URL` and `CADRE_AI_MODEL`; it must never call OpenRouter directly from CADRE. Record only pass/fail and sanitized model metadata without logging provider credentials, request headers, prompts, responses, or upstream error bodies. A missing OpenRouter key or stopped gateway blocks only this external live check, not format, lint, TypeScript, deterministic tests, build, or application process health.

## AI routing controls

- Keep the Phase 1 default at `cadre-free`.
- Maintain LiteLLM concurrency, request-rate, timeout, retry, failure, and cooldown bounds.
- Keep premium fallback disabled so a free-route failure cannot silently create paid usage.
- Apply the enforceable Phase 1 spending limit to the OpenRouter key.
- Do not treat LiteLLM budget configuration as an enforceable cap without its PostgreSQL spend-tracking database; it fails open when that database is absent.
- Do not enable multiple LiteLLM workers until shared rate-limit state is justified and provided.

## Routine operation

- Review failed and approval-blocked jobs.
- Confirm Ready Dock rows open the exact persisted artifact.
- Review active sessions and revoke unexpected access.
- Review audit events for administrative and approval actions.
- Review OpenRouter key usage and its provider-side spending limit.
- Confirm gateway logs contain no prompts, responses, authorization headers, or provider keys.
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
