# CADRE

CADRE is the private, owner-operated parent AI platform for governed workspaces across the Cho Zen Dell ecosystem. Foundation v0.1 is local-first: it provides a secure application boundary for workspaces, persistent conversations, Markdown artifacts, durable job state, notifications, audit history, and a Ready Dock without treating application data as canonical doctrine.

VESSEL is an initial workspace and future flagship application. It is not CADRE, and the full VESSEL application is outside this foundation.

## Current status

- Canonical workspace: `/Users/wendellionaire/Library/Mobile Documents/com~apple~CloudDocs/cadre`
- Git: initialized with a baseline on `main`; foundation work is on `feat/cadre-platform-foundation`; no remote is configured or verified.
- Runtime: Next.js 16, React 19, TypeScript, Drizzle ORM, and a PostgreSQL-compatible local store.
- AI: OpenAI through a server-only provider boundary. The credential is present, but the live readiness check is blocked by project quota (`HTTP 429`).
- Deployment: local only. VPS, domains, TLS, reverse proxy, backups, and public availability are unverified and deferred.
- Canonical knowledge: the existing Wendellionaire Obsidian vault remains authoritative. This repository does not duplicate or replace locked doctrine.

See [CURRENT_ENVIRONMENT_REPORT.md](docs/CURRENT_ENVIRONMENT_REPORT.md) for the evidence-backed checkpoint.

## Local setup

Requirements:

- Node.js 20.9 or newer
- npm
- A private `.env.local` containing required server-only values

```bash
npm ci
npm run verify:env
npm run db:migrate
npm run db:seed
npm run owner:create
npm run dev
```

Open `http://localhost:3000`. Do not expose the development server publicly.

The owner bootstrap command is interactive. Never place a password, API key, session token, or recovery credential in command history, source code, logs, screenshots, or chat.

## Validation

```bash
npm run validate
npm run test:e2e
```

The live OpenAI integration test is intentionally separate because it uses provider credentials and may incur usage:

```bash
npm run test:openai
```

Passing local checks establishes only the state those checks actually exercised. It does not establish public-deployment readiness.

The deterministic desktop and mobile end-to-end flow passes locally. A real operator account still requires the interactive `npm run owner:create` bootstrap, and live OpenAI activation requires available quota for the configured Platform project.

## Authority boundary

- Obsidian: doctrine, approved canonical knowledge, decisions, standards, project state, and promotion authority.
- This Git repository: CADRE application source, migrations, tests, and technical release state.
- Database: operational users, sessions, workspaces, conversations, jobs, notifications, audit events, and artifact metadata.
- Artifact storage: exact payload bytes, versions, and checksums.
- OpenAI: inference service only; never a canonical database.

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
