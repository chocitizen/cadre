# Database Schema

## Purpose

The database stores CADRE operational state. It does not replace the canonical Obsidian knowledge system or grant Source-of-Truth authority.

Local development uses the configured PostgreSQL-compatible embedded store when `DATABASE_URL` is absent. A private PostgreSQL service is the intended production database, but no production service is currently provisioned or verified.

## Core entities

| Entity                | Purpose                       | Required relationships and controls                                                                     |
| --------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------- |
| users                 | Owner/admin identity          | Unique normalized email, scrypt password hash, active state, role, timestamps                           |
| sessions              | Revocable authentication      | User, hashed opaque and CSRF tokens, user-agent hash, idle/absolute expiry, revocation                  |
| auth_throttles        | Login abuse control           | Hashed identifier, attempt window, count, block expiry, timestamps                                      |
| workspaces            | Operational separation        | Stable slug, display name, description, active state, canonical project reference                       |
| workspace_memberships | Role-ready access             | User, workspace, role, timestamps; unique membership                                                    |
| conversations         | Persistent chat container     | Workspace, owner, title, provider/model metadata, timestamps                                            |
| messages              | Ordered conversation history  | Conversation, role, content, provider/model and retrieval metadata, timestamps                          |
| artifacts             | Durable output identity       | Workspace, conversation, source job, type, title, current version, approval state, timestamps           |
| artifact_versions     | Immutable artifact revision   | Artifact, version, content or external key, MIME type, byte size, SHA-256 checksum, provenance, creator |
| jobs                  | Honest durable work state     | Workspace, conversation, operation, status, progress, result/error metadata, timestamps                 |
| job_artifacts         | Job-output relationship       | Job and artifact IDs; unique relationship                                                               |
| notifications         | User-visible state change     | User, workspace, job, artifact, type, status, read/opened timestamps                                    |
| audit_events          | Material-action evidence      | Actor, workspace, action, target, authority, result, redacted metadata, timestamp                       |
| ready_dock_items      | Read-only delivery projection | SQL view over jobs, artifacts, notifications, workspaces, and originating conversations                 |

## Integrity rules

- Use stable durable IDs and foreign keys.
- Scope conversation, artifact, job, and notification access through workspace authorization.
- Use constrained status vocabularies rather than ambiguous free text.
- Prevent duplicate workspace slugs and duplicate memberships.
- Keep message ordering deterministic.
- Keep artifact version and checksum immutable for a given stored revision.
- Represent a new artifact revision as lineage, not silent overwrite.
- Never persist API keys, session plaintext, passwords, recovery codes, or unnecessary provider payloads.
- Cascade only when deletion behavior is explicit and recoverable; preserve audit evidence as required.

## Ready Dock query

`ready_dock_items` is an existing SQL view over jobs, artifacts, notifications, workspaces, and originating conversations. It is not a second persistence model. It maps exact job states to user-facing Dock categories and exposes the current artifact, action path, unread state, and allowed actions.

## Migrations and seeding

```bash
npm run db:migrate
npm run db:seed
```

Migrations must be additive where practical and paired with a rollback or restore decision. Seeded workspaces are operational containers only; they do not assert that the corresponding project is canonical or complete.

## Deferred schema

Vector embeddings, governed tool/prompt registries beyond the fixed foundation prompt version, external integration credentials, object-storage lifecycle, durable worker leases, retry schedules, and cross-workspace retrieval are deferred until a validated workflow requires them.
