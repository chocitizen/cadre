# Architecture

## Objective

Foundation v0.1 provides the smallest production-shaped local CADRE platform that can authenticate an owner, preserve workspace conversations, call a configured AI gateway through a provider-neutral boundary, retain a Markdown artifact, and surface durable work in the Ready Dock.

CADRE Core remains a modular monolith. Next.js owns the web interface and server boundary. Application services own authorization and use cases. Repository adapters own persistence. AI routing remains behind the existing service interface and passes through one separately managed LiteLLM loopback gateway. No additional CADRE microservices, Redis, vector database, or provider-specific application adapters are justified at this stage.

## System layers

1. **Governance references** — links to the canonical Obsidian doctrine, source-of-truth records, validation requirements, and authority constraints.
2. **Web interface** — authenticated workspace, conversation, artifact, and Ready Dock surfaces.
3. **Application services** — authorization, validation, use-case coordination, status transitions, and audit creation.
4. **AI gateway boundary** — one server-side LiteLLM adapter plus an explicitly test-only deterministic adapter. Provider credentials and routing policy remain outside browser code.
5. **Persistence** — Drizzle-managed operational records in a PostgreSQL-compatible local store or PostgreSQL.
6. **Artifact boundary** — durable content plus artifact identity, version, approval state, provenance, and checksum.
7. **External authority boundary** — Obsidian, Git, future object storage, and future deployment infrastructure remain controlled adapters rather than scattered integration logic.

Current server boundaries live under `src/server/`: authentication and workspace authorization in `auth/`, Drizzle and database adapters in `db/`, AI contracts/providers in `ai/`, artifact preparation in `artifacts/`, audit persistence in `audit/`, job transitions in `jobs/`, and the deliberately disabled Obsidian adapter in `integrations/obsidian/`.

## AI routing

```text
CADRE server
  -> AI provider contract
  -> LiteLLM 1.95.0 at 127.0.0.1:4000
  -> cadre-free
  -> OpenRouter free-model router
```

Phase 1 uses `cadre-free` as the default CADRE-facing model alias. The underlying OpenRouter model is selected through environment-backed LiteLLM configuration, so it can change without application-code changes. OpenAI is not part of the default runtime path and requires neither an OpenAI key nor OpenAI billing.

Two future lanes are preserved without being activated:

- `cadre-local` may route to a verified local or self-hosted runtime after one exists.
- `cadre-premium` may route through OpenRouter or a direct provider only after explicit provider and spending approval.

Premium fallback is disabled by default. Phase 1 therefore cannot silently escalate from a free route into paid inference. The committed LiteLLM configuration supplies bounded concurrency, request rate, timeout, retry, failure, and cooldown controls. Model fallbacks are activated only when their destination lane has been separately approved and verified.

LiteLLM spend budgets are not an enforceable Phase 1 ceiling because their tracking requires LiteLLM's PostgreSQL database and fails open without it. The actual Phase 1 spending limit belongs on the OpenRouter key. Adding LiteLLM PostgreSQL or Redis is deferred until durable spend accounting or shared multi-worker rate-limit state is justified.

The gateway binds to loopback, uses server-only credentials, and must not log prompts, responses, authorization headers, or provider keys. Its launcher forwards only active OpenRouter and necessary host/TLS variables, so an inactive direct-provider key cannot enable a passthrough route by mere presence. Any approved non-loopback gateway must use HTTPS. No gateway or provider secret may be exposed through browser code.

## Core flow

```text
Owner session
  -> authorized workspace
  -> conversation and persisted user message
  -> AI service boundary and configured LiteLLM model alias
  -> persisted assistant message and provider metadata
  -> optional durable job
  -> Markdown artifact and notification
  -> Ready Dock
```

The request path completes inline in v0.1. A durable job record reflects the actual state transitions; `worker` is schema-ready but no background worker is implemented. The interface must never imply one exists.

## Authority design

Application availability is separate from CADRE invocation. An invocation or mission begins with objective, source-of-truth reference, authorized scope, locked elements, validation level, and human-approval requirement. It ends with a recorded result, validation, write-back decision, and disbandment.

The canonical models are referenced from:

- `MASTER OPERATING DOCTRINE/CADRE Integration V2.md`, sections II-IV, XV-XVII, and XXI.
- `MASTER OPERATING DOCTRINE/CADRE Invocation & Assembly Protocol.md`, sections I-III, VI-IX, XVII-XVIII, and XXII-XXIV.
- `MASTER OPERATING DOCTRINE/CADRE Mission Control.md`, sections I-III, XIX, XXIII-XXIV, and XXVII-XXVIII.

These files live under `/Users/wendellionaire/Documents/Wendellionaire/` and are referenced, not copied.

## Deployment shape

Local development uses the Next.js process, local PostgreSQL-compatible data, and—only for live AI—a LiteLLM gateway bound to loopback. `next.config.ts` declares standalone output for a future controlled host. No public host, container runtime, reverse proxy, TLS certificate, or production service manager has been selected or verified.

See [DEPLOYMENT.md](DEPLOYMENT.md) before treating the standalone build as deployable infrastructure.
