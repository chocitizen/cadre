# Deployment

## Current status

Deployment is local only.

The repository can produce a standalone Next.js build, but no VPS, SSH target, domain, DNS record, TLS certificate, reverse proxy, container runtime, process manager, production PostgreSQL service, firewall policy, monitoring system, or backup service has been supplied or verified.

Do not claim CADRE is hosted, reachable, production ready, or backed up.

## Local build

```bash
npm ci
npm run validate
npm run build
npm run start
```

This validates only the local environment exercised by the commands.

## Required production inputs

Before selecting or changing deployment architecture, obtain and verify:

- authorized host name or address and account;
- operating system and supported runtime;
- CPU, memory, storage, and disk headroom;
- firewall, listening ports, SSH policy, and privilege model;
- domain and DNS authority;
- TLS termination and certificate renewal;
- private PostgreSQL service and network path;
- a private LiteLLM runtime, loopback or private-network binding, and service supervision;
- provider-account ownership, key recovery, and an enforceable provider-side spending limit;
- process supervision and restart policy;
- logs, monitoring, alerts, and retention;
- encrypted backups and a tested restore;
- release, migration, and rollback procedure;
- ownership, recovery, and access-revocation records.

The absence of Docker locally is not a reason to add it. Choose a deployment mechanism only after the authorized target is inspected.

## Runtime configuration

Production requires server-only values for the database, exact public origin, LiteLLM gateway URL and authentication, CADRE model alias, and only the provider credentials for explicitly enabled routes. Secrets must be supplied through the host's protected secret mechanism, never copied from `.env.local` into source control or build artifacts.

The approved Phase 1 runtime is CADRE server → LiteLLM 1.95.0 → OpenRouter's free-model router through the `cadre-free` alias. Bind LiteLLM to loopback when it shares the host with CADRE. `CADRE_AI_GATEWAY_API_KEY`, `OPENROUTER_API_KEY`, and any future provider key remain server-only; none may use a `NEXT_PUBLIC_` prefix or enter a browser bundle. An OpenAI key and OpenAI billing are not required.

The local gateway configuration lives at `config/litellm.yaml`. Local/self-hosted and premium/direct-provider lanes remain inactive until separately authorized and verified. Premium fallback stays disabled by default. LiteLLM's rate, timeout, retry, failure, and cooldown controls are routing safeguards, not a spending guarantee. Without LiteLLM PostgreSQL, its budget control fails open; Phase 1 must use an enforceable limit on the OpenRouter key itself.

Set secure cookie behavior under HTTPS, restrict the database from public access, run the application as a non-root service account, and permit only required inbound ports.

## Release gate

Before release, verify:

- clean, reviewed commit and reproducible install;
- format, lint, type, unit, integration, end-to-end, and build checks;
- owner authentication, session expiry/revocation, and route protection;
- database migration and rollback compatibility;
- persistent conversation and artifact reopen flow;
- accurate Ready Dock state;
- security headers, origin enforcement, rate limiting, and error redaction;
- gateway loopback/private-network isolation, provider-side spending limits, and prompt/response log exclusion;
- TLS, firewall, service account, and database isolation;
- backup success and restore evidence;
- monitoring and incident response;
- exact deployed commit and post-deploy health.

Push, remote creation, deployment, DNS changes, VPS mutation, and public exposure require a verified target and explicit authorization. They are deferred at this checkpoint.
