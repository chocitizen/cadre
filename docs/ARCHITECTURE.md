# Architecture

## Objective

Foundation v0.1 provides the smallest production-shaped local CADRE platform that can authenticate an owner, preserve workspace conversations, call one AI provider through a boundary, retain a Markdown artifact, and surface durable work in the Ready Dock.

It is a modular monolith. Next.js owns the web interface and server boundary. Application services own authorization and use cases. Repository adapters own persistence. Provider-specific AI code remains behind a service interface. No microservices, Redis, vector database, or separate API service are justified at this stage.

## System layers

1. **Governance references** — links to the canonical Obsidian doctrine, source-of-truth records, validation requirements, and authority constraints.
2. **Web interface** — authenticated workspace, conversation, artifact, and Ready Dock surfaces.
3. **Application services** — authorization, validation, use-case coordination, status transitions, and audit creation.
4. **AI provider boundary** — one server-side OpenAI adapter plus an explicitly test-only deterministic adapter.
5. **Persistence** — Drizzle-managed operational records in a PostgreSQL-compatible local store or PostgreSQL.
6. **Artifact boundary** — durable content plus artifact identity, version, approval state, provenance, and checksum.
7. **External authority boundary** — Obsidian, Git, future object storage, and future deployment infrastructure remain controlled adapters rather than scattered integration logic.

Current server boundaries live under `src/server/`: authentication and workspace authorization in `auth/`, Drizzle and database adapters in `db/`, AI contracts/providers in `ai/`, artifact preparation in `artifacts/`, audit persistence in `audit/`, job transitions in `jobs/`, and the deliberately disabled Obsidian adapter in `integrations/obsidian/`.

## Core flow

```text
Owner session
  -> authorized workspace
  -> conversation and persisted user message
  -> AI service boundary
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

Local development uses the Next.js process and local PostgreSQL-compatible data. `next.config.ts` declares standalone output for a future controlled host. No host, container runtime, proxy, TLS certificate, or production service manager has been selected or verified.

See [DEPLOYMENT.md](DEPLOYMENT.md) before treating the standalone build as deployable infrastructure.
