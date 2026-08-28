# LANSEIR / CADRE Architecture

## Request path

```text
Browser
  -> Caddy HTTPS / bounded public ingress
  -> FastAPI request ID, security headers, rate/body policy
  -> browser session + CSRF OR service bearer identity
  -> domain route + ownership/role authorization
  -> SQLAlchemy domain model
  -> PostgreSQL (production) / SQLite (local validation)
```

LANSEIR owns the customer experience. CADRE owns internal orchestration,
specialist definitions, run state, service registries, and operations truth.

Authorized operational interfaces enter through the Universal Prompt Gateway:

```text
raw input -> service identity -> command semantics -> canonical context
  -> doctrine + approvals/locks -> specialist assembly -> adapter capability
  -> governed action -> evidence/validation -> state + provenance -> next action
```

The gateway writes to the existing Command Brief, Mission Control, audit, and
execution-state records. It does not maintain a parallel task graph. See
`docs/UNIVERSAL_PROMPT_GATEWAY.md`.

## Identity boundary

Passwords use salted scrypt. The browser receives an opaque HttpOnly session
cookie and a separate CSRF cookie; mutating authenticated requests must echo
the CSRF value in `X-CSRF-Token`. The database stores only SHA-256 session and
CSRF token hashes. Admin authorization is enforced server-side. Account export
and deletion are authenticated operations.

Service-role bearer tokens are a separate machine boundary. The Founder role
may approve exact gateway references and alter protected execution state.
Doctrine reads are limited to Mission Control, Al, and Griot. Project,
command-brief, and operations state reads are limited to authorized operating
roles. Mission Control and Al retain bounded registry-write authority.

## Product domains

- Publishing: books, chapters, entitlements, reading/audio progress
- Personal context: private notes, bookmarks, Captain's Log
- Guided development: Voyages, ordered lessons, enrollments, reflections
- Intelligence: conversations, messages, provider results, specialist runs
- Operations: support requests, audit events, M1 registries, host state

Every private record query includes the authenticated owner. Content is
released only when both publication state and entitlement permit it.

## AI routing

`local` is deterministic, zero-cost, and the default. The OpenAI-compatible
adapter supports approved OpenAI, OpenRouter, LiteLLM, or local gateways via a
validated HTTPS/loopback base URL. Routes record provider, model, latency,
usage metadata, and failure state. Provider keys remain server-side.

AI context is explicitly constructed by conversation type. Captain's Log is
not an allowed AI context type. Notes, books/chapters, and Voyage reflections
are included only when owned/entitled by the active user.

## Operations

The root-owned controller accepts typed allowlisted operations, verifies exact
canonical Git ancestry, materializes bounded archives, activates atomically,
checks release identity, and rolls back to a verified last-known-good release.
Protected logs and mutations require durable intent and terminal receipts.

Production dependencies are wheel-hash locked and service/base images are
digest pinned. Refreshes require deliberate review and provenance updates.
