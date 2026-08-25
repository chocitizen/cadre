# CADRE

CADRE is the private, owner-operated parent AI platform for governed workspaces across the Cho Zen Dell ecosystem. Foundation v0.1 is local-first: it provides a secure application boundary for workspaces, persistent conversations, Markdown artifacts, durable job state, notifications, audit history, and a Ready Dock without treating application data as canonical doctrine.

VESSEL is an initial workspace and future flagship application. It is not CADRE, and the full VESSEL application is outside this foundation.

## Current status

- Canonical workspace: `/Users/wendellionaire/Library/Mobile Documents/com~apple~CloudDocs/cadre`
- Git: initialized with a baseline on `main`; foundation work is on `feat/cadre-platform-foundation`; no remote is configured or verified.
- Runtime: Next.js 16, React 19, TypeScript, Drizzle ORM, and a PostgreSQL-compatible local store.
- AI: CADRE routes server-side requests through a pinned LiteLLM 1.95.0 loopback gateway. Phase 1 selects the `cadre-free` alias, which uses OpenRouter's free-model router. OpenAI is optional and disabled unless explicitly configured.
- Live AI: the architecture and configuration are present, but an external completion remains blocked until an OpenRouter key is supplied securely and the LiteLLM gateway is launched.
- Deployment: local only. VPS, domains, TLS, reverse proxy, backups, and public availability are unverified and deferred.
- Canonical knowledge: the existing Wendellionaire Obsidian vault remains authoritative. This repository does not duplicate or replace locked doctrine.

See [CURRENT_ENVIRONMENT_REPORT.md](docs/CURRENT_ENVIRONMENT_REPORT.md) for the evidence-backed checkpoint.

## Local setup

Requirements:

- Node.js 20.9 or newer
- npm
- Python 3.10 through 3.14 for the LiteLLM gateway
- A private `.env.local` containing required server-only values

```bash
npm ci
npm run ai:gateway:install
npm run verify:env
npm run db:migrate
npm run db:seed
npm run owner:create
npm run dev
```

On Intel macOS, the pinned LiteLLM package may build from source and therefore also needs the Xcode Command Line Tools; its build backend may bootstrap Rust into the user's cache. `CADRE_PYTHON` is a command-scoped installer override—the installer does not load it from `.env.local`. When the default `python3` is outside the supported range, run `CADRE_PYTHON=/absolute/path/to/python3.12 npm run ai:gateway:install`.

Open `http://localhost:3000`. Do not expose the development server publicly.

For live AI, place the OpenRouter credential in `.env.local`, then start the gateway in a separate private terminal:

```bash
npm run ai:gateway:start
```

The gateway binds to `127.0.0.1:4000`. CADRE calls its `cadre-free` model alias; changing the underlying model is a configuration change, not an application-code change.

The owner bootstrap command is interactive. Never place a password, API key, session token, or recovery credential in command history, source code, logs, screenshots, or chat.

## Validation

```bash
npm run validate
npm run test:e2e
```

The live AI integration test is intentionally separate because it calls the configured gateway and an external provider:

```bash
npm run test:ai:live
```

Passing local checks establishes only the state those checks actually exercised. It does not establish public-deployment readiness.

The deterministic desktop and mobile end-to-end flow passes locally. A real operator account still requires the interactive `npm run owner:create` bootstrap. Live external inference additionally requires a securely supplied OpenRouter key and a running LiteLLM gateway; no OpenAI key or OpenAI billing is required.

## Authority boundary

- Obsidian: doctrine, approved canonical knowledge, decisions, standards, project state, and promotion authority.
- This Git repository: CADRE application source, migrations, tests, and technical release state.
- Database: operational users, sessions, workspaces, conversations, jobs, notifications, audit events, and artifact metadata.
- Artifact storage: exact payload bytes, versions, and checksums.
- LiteLLM and its configured model providers: inference routing only; never a canonical database or authority source.

Read [DATA_AUTHORITY.md](docs/DATA_AUTHORITY.md) and [OBSIDIAN_BOUNDARY.md](docs/OBSIDIAN_BOUNDARY.md) before adding retrieval, synchronization, or write-back.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Database schema](docs/DATABASE_SCHEMA.md)
- [Data authority](docs/DATA_AUTHORITY.md)
- [Security](docs/SECURITY.md)
- [Ready Dock](docs/READY_DOCK.md)
- [Obsidian boundary](docs/OBSIDIAN_BOUNDARY.md)
- [Operations](docs/OPERATIONS.md)
- [Backup, restore, and rollback](docs/BACKUP_RESTORE_ROLLBACK.md)
- [Deployment](docs/DEPLOYMENT.md)
