# Data Authority

## Governing rule

No two systems silently claim authority over the same data class. A database field named `canonical_status` or `approval_state` records metadata; it cannot promote an asset or decision by itself.

## Authority matrix

| Data class                             | Authoritative system                                         | CADRE database role                                                           | Authorized writer                         |
| -------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------- | ----------------------------------------- |
| Master doctrine and Sovereignty        | Canonical Obsidian vault                                     | Store a reference, version, classification, and retrieval evidence only       | Human-governed vault change process       |
| Source-of-truth registry and promotion | Canonical Obsidian vault                                     | Record requested/proposed write-back and resulting reference                  | Authority named in the registry           |
| Project and brand truth                | Obsidian project home, State Card, decisions, and registries | Operational workspace projection and links                                    | Governed project authority                |
| CADRE source code and migrations       | This Git repository                                          | None                                                                          | Authorized repository operator            |
| Users, credentials, and sessions       | CADRE operational database                                   | Primary operational record                                                    | Server-side authentication service        |
| Conversations and messages             | CADRE operational database                                   | Primary operational record, subject to retention                              | Authorized user and application service   |
| Jobs and notifications                 | CADRE operational database                                   | Primary operational record                                                    | Application service within explicit scope |
| Audit events                           | CADRE operational database and future protected export       | Append-only operational evidence                                              | Server-side audited actions               |
| Artifact metadata                      | CADRE operational database                                   | Durable ID, workspace, lineage, version, state, checksum, and storage pointer | Artifact service within scope             |
| Markdown artifact payload              | CADRE operational database in v0.1                           | Versioned content, MIME type, byte size, SHA-256, and provenance              | Artifact service within scope             |
| Transient request/cache state          | Process memory or future queue/cache                         | Never authoritative                                                           | Application runtime                       |
| Model output and provider metadata     | CADRE operational database; no canonical authority           | Persisted message plus minimum provider/model/usage metadata                  | AI service adapter                        |

## Status namespaces

Keep these domains separate:

- `canonical_status`: Working, Validated, Approved, Locked, The Now, Superseded, Archived.
- `job_status`: queued, running, needs_approval, review, ready, failed, delivered, archived.
- `artifact_approval_state`: draft, review, approved, rejected, archived.
- `notification_status`: unread, read, archived.

A `ready` job is not an approved artifact. An approved artifact is not automatically The Now. The Now requires the canonical promotion process.

The optional canonical-status label inside artifact provenance is descriptive evidence only. It does not update the vault or grant promotion authority.

## AI and retrieval

Semantic similarity, conversation history, generated summaries, and provider memory never outrank a canonical source classification. Retrieval must preserve the originating path, version, classification, and provenance. Only the minimum necessary private context may be sent to an AI provider.

## Promotion boundary

CADRE may create a proposal containing the candidate, reason, evidence, change scope, locked elements, dependencies, validation, and requested decision. Promotion remains outside automatic runtime authority until the required human approves it and the canonical registry is updated.

Canonical references:

- `MASTER OPERATING DOCTRINE/Source of Truth Registry.md`, sections I-II and V-XII.
- `MASTER OPERATING DOCTRINE/Change Control & Versioning.md`, sections II, XIII, XXII, and XXIV.
- `MASTER OPERATING DOCTRINE/Knowledge Architecture & Obsidian Protocol.md`, sections XVII and XXII-XXVIII.
