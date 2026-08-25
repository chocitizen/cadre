# Current Environment Report

Date: 2026-08-25

Scope: local CADRE foundation checkpoint

## Executive state

CADRE was established in the existing selected folder. Legitimate pre-existing work was preserved. Git is initialized directly at the workspace root; no nested repository was created. Foundation v0.1 is implemented and locally validated with an isolated deterministic provider. The AI boundary is configured for CADRE server → LiteLLM 1.95.0 loopback gateway → OpenRouter free-model router through the `cadre-free` alias. The isolated gateway runtime is installed, and loopback startup, liveness, and readiness are verified. The environment remains local-only, and no VPS or public deployment has been verified. Live external completion is currently blocked because no OpenRouter key is configured; it must be revalidated after the key is supplied securely and the gateway is running.

## Local environment

| Area                       | Verified state                                                                          |
| -------------------------- | --------------------------------------------------------------------------------------- |
| Workspace                  | `/Users/wendellionaire/Library/Mobile Documents/com~apple~CloudDocs/cadre`              |
| Host                       | macOS 12.7.6, Intel                                                                     |
| Git                        | 2.37.1; baseline on `main`; active branch `feat/cadre-platform-foundation`; no remote   |
| Node/npm                   | Node 24.18.0; npm 11.16.0                                                               |
| Other runtime              | pnpm 11.19.0; system Python 3.9.6; isolated gateway Python 3.12.13                      |
| AI gateway                 | LiteLLM 1.95.0 installed; loopback startup plus liveness/readiness verified             |
| Gateway runtime gate       | `.venv-litellm` is installed and ignored; fresh setup requires Python 3.10 through 3.14 |
| Local secret file          | `.env.local` exists with mode `600`; ignored and untracked                              |
| OpenRouter credential      | Not supplied or verified; no plaintext value was inspected                              |
| OpenAI credential          | Optional and unused by the Phase 1 route; OpenAI billing is not required                |
| Containers                 | Docker and Docker Compose not installed                                                 |
| External data services     | PostgreSQL and Redis clients/services not present locally                               |
| Web/process infrastructure | Nginx, Caddy, Traefik, PM2, and Supervisor not present                                  |
| Remote access              | No VPS host, alias, address, account, or SSH configuration was supplied or verified     |
| Public deployment          | Not implemented or verified                                                             |

No secret value was displayed, logged, or inspected during the gateway change. Any previously stored OpenAI credential remains private, is not consulted by the Phase 1 route, and is excluded from the LiteLLM child-process environment. External inference will be validated only through the loopback LiteLLM gateway after an OpenRouter key is supplied securely; CADRE will not call OpenRouter directly.

## Application foundation

The repository declares:

- Next.js 16.3.2 and React 19.2.8;
- strict TypeScript;
- Drizzle ORM with PostgreSQL and an embedded PostgreSQL-compatible local option;
- LiteLLM behind the existing provider/service boundary, with OpenRouter's free-model router as the Phase 1 external lane;
- Zod validation;
- Vitest and Playwright validation;
- standalone Next.js output for a future controlled deployment;
- security headers, same-origin mutation controls, and server-only secrets.

The local environment uses `CADRE_DB_PATH` when `DATABASE_URL` is absent. Production PostgreSQL is a target, not a currently verified service.

At this checkpoint, the tree contains the database migrations/schema, local PGlite/PostgreSQL adapter, workspace seeds, interactive owner bootstrap, authentication and authorization, provider-neutral AI contracts and a LiteLLM gateway adapter, a pinned LiteLLM configuration, persistent workspace chat, versioned Markdown artifacts with checksums and provenance, durable job state, notifications, audit persistence, Ready Dock, responsive PWA shell, and a disabled Obsidian adapter boundary.

## Canonical systems discovered

The active Obsidian vault is `/Users/wendellionaire/Documents/Wendellionaire`. It remains the canonical knowledge system. The most relevant authoritative records are:

- `MASTER OPERATING DOCTRINE/Master_Operating_Doctrine_v1.2.md` — preservation, scoped authority, source-of-truth, validation, inheritance, and sovereignty laws.
- `MASTER OPERATING DOCTRINE/CADRE Integration V2.md` — CADRE system position, activation gate, invocation contract, orchestration, validation, and write-back.
- `MASTER OPERATING DOCTRINE/CADRE Invocation & Assembly Protocol.md` — minimum sufficient specialist assembly, authority, validation, approval, and exit.
- `MASTER OPERATING DOCTRINE/CADRE Mission Control.md` — mission state, authoritative context, validation gates, closeout, and disbandment.
- `MASTER OPERATING DOCTRINE/Source of Truth Registry.md` — current authority and promotion state.
- `MASTER OPERATING DOCTRINE/Change Control & Versioning.md` — Past / The Now / Next and promotion controls.
- `MASTER OPERATING DOCTRINE/Knowledge Architecture & Obsidian Protocol.md` — Obsidian retrieval and write-back rules.
- `13 — System Directory & File Architecture.md` — external code repository and one-source/many-interfaces boundaries.

No canonical record identifies a CADRE application repository, production database, VPS, domain, or deployed service as approved or operational.

## Reconciliation

| Classification | Components                                                                                                                                                                                                             | Decision                                                                                                                   |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| REUSE          | Locked Doctrine and Sovereignty; Source of Truth; Change Control; validation, risk, and automation rules; registries                                                                                                   | Reference and enforce without copying or rewriting.                                                                        |
| REUSE          | Vault validation and canonical-package tooling                                                                                                                                                                         | Use in the vault for its governed purpose; do not copy it into this application.                                           |
| EXTEND         | Artifact provenance, checksums, audit evidence, operational status                                                                                                                                                     | Implement application records that preserve the canonical concepts without granting promotion authority.                   |
| ADAPT          | Mission Control, invocation, routing, authority levels, project lifecycle, and State Cards                                                                                                                             | Express them as application schemas and interfaces while preserving their meaning.                                         |
| ADD            | Local Git; owner authentication; AI gateway boundary; LiteLLM/OpenRouter free route; operational database; persistent chat; Markdown artifact workflow; jobs, notifications, audits, and Ready Dock                    | Required for Foundation v0.1 and approved Phase 1 AI routing.                                                              |
| DEFER          | Activated local/self-hosted lane; premium/direct-provider lane; LiteLLM PostgreSQL/Redis; bidirectional Obsidian sync; pgvector; object storage service; native apps; full VESSEL; VPS/public deployment; remote CI/CD | Add only after an evidenced requirement, explicit economic approval where applicable, and an authorized environment exist. |

## Conflicts resolved

1. CADRE is an intelligence and execution engine beneath the Master Operating Doctrine, not the authority that owns or rewrites doctrine.
2. PostgreSQL owns operational application records, not canonical knowledge.
3. An available CADRE web service does not mean a CADRE mission is always active; missions retain explicit invocation and disbandment states.
4. Runtime workspace and job statuses do not confer canonical approval.
5. A prior Majestic Lifestyle infrastructure image is unregistered reference material, not verified CADRE infrastructure.

## Current gaps and gates

- A remote repository is not configured or verified.
- VPS access and configuration are unavailable.
- No real operator account has been bootstrapped; that password must be entered interactively and never through chat.
- The system Python remains below LiteLLM's supported range; the installed isolated gateway instead uses Python 3.12.13.
- An OpenRouter key has not been supplied or verified. The live gateway check reached OpenRouter through LiteLLM and stopped safely at HTTP 401.
- TLS, firewall, reverse proxy, production database, monitoring, independent backups, and restore tests are unverified.
- Public deployment is not authorized by the current evidence.
- Obsidian write-back remains a governed future operation, not an automatic application behavior.

## Validation state

The preserved foundation and provider-neutral gateway change were verified locally on 2026-08-25:

- formatter, ESLint, strict TypeScript, and production Next.js standalone build passed;
- 28 unit/integration tests across 7 files passed;
- both database migrations applied and the eight-workspace seed remained idempotent;
- authentication, session revocation, CSRF, throttling, workspace authorization, persistence, chat, artifact creation/retrieval, job transitions, notifications, and Ready Dock passed automated tests;
- the required owner → VESSEL → conversation → AI response → reopen → Markdown artifact → Ready Dock → artifact reopen flow passed in desktop and mobile Chromium;
- in-app desktop/mobile visual inspection passed with no browser errors or warnings;
- `npm audit --audit-level=low` reported zero known vulnerabilities;
- the source-controlled secret scan passed across 116 candidate files;
- `.env.local` remained mode `600`, ignored, and untracked; the key value was never displayed;
- the previous direct-OpenAI live check reached its provider boundary and failed safely with HTTP 429; that historical result no longer defines the approved runtime path.

The LiteLLM change passed the full deterministic validation suite and source-controlled secret scan. The isolated Python dependency graph passed `pip check`; LiteLLM started on loopback, and both `/health/liveliness` and `/health/readiness` returned HTTP 200. The separate `npm run test:ai:live` attempt reached OpenRouter through the configured `cadre-free` gateway route and returned sanitized HTTP 401 because no OpenRouter credential is configured. This blocks only external inference, not CADRE startup, deterministic validation, or application/database health.

## Minimal execution path

1. Create an OpenRouter key with an enforceable provider-side spending limit, then save it securely as `OPENROUTER_API_KEY` in `.env.local`; never paste it into chat or source control.
2. Launch the installed loopback gateway with `npm run ai:gateway:start`.
3. Run `npm run test:ai:live` and record only sanitized pass/fail evidence.
4. Create the real owner interactively with `npm run owner:create`.
5. Keep the application in Working/Next state until explicit approval.
6. Propose, rather than automatically perform, canonical Obsidian write-back.
7. Obtain an explicit private remote and VPS target before any push or deployment.
