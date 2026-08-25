# Security

## Current security posture

CADRE Foundation v0.1 is private and local-first. It is not approved for public exposure. The application uses server-only configuration, same-origin mutation checks, protected routes, secure session handling, input validation, security headers, and audit records for material actions.

This is a development security baseline, not evidence of a hardened production environment.

## Secrets

- Store local credentials only in `.env.local`.
- `.env`, `.env.local`, and `.env.*.local` are ignored by Git.
- `.env.local` is untracked and should remain mode `600`.
- Never use a `NEXT_PUBLIC_` prefix for a secret.
- Never print, echo, return, serialize, snapshot, commit, or place secrets in audit events.
- Diagnostic checks report only `PRESENT`, `MISSING`, or `MISCONFIGURED`.
- `.env.example` contains names and safe defaults only.

The OpenAI adapter receives the key server-side. Browser code, persisted messages, artifacts, job errors, and application logs must never contain it.

## Authentication and authorization

- Begin with one owner/admin account; do not overbuild enterprise identity.
- Store only a salted scrypt password hash, never plaintext credentials. The current minimum is 14 characters.
- Use 256-bit opaque session and CSRF tokens; persist only their SHA-256 hashes.
- Apply HTTP-only, SameSite=Lax session cookies and a `__Host-` secure cookie name in production TLS environments.
- Enforce the current 12-hour idle and seven-day absolute session limits plus server-side revocation.
- Track authentication throttling by a hashed identifier, never a plaintext password or raw token.
- Authorize every server mutation against the authenticated user and workspace.
- Do not infer authority from a role name, expertise, a generated result, or the existence of a workspace.

## Request and browser controls

The current Next.js configuration applies CSP, frame denial, MIME sniffing protection, a strict referrer policy, and restricted browser permissions. API responses are marked `no-store`. Server actions are capped at 1 MB.

State-changing requests enforce exact same-origin and CSRF checks and validate structured input. File uploads are not part of the current minimum artifact workflow; any future upload path requires type, size, authorization, malware, storage, and download controls.

## AI privacy

- Send only the minimum context needed for the request.
- Do not bulk-send the Obsidian vault.
- Keep provider code behind the AI service boundary.
- Treat model output as untrusted until validated.
- Preserve provider/model/request metadata without storing credentials.
- Use `store: false` for OpenAI Responses requests.
- Never treat provider conversation state as canonical memory.

## Logging and audit

Audit material events: authentication, workspace changes, artifact creation, job transitions, administrative changes, and approval actions. Record actor, time, authority source, target, result, and relevant IDs. Redact secrets, credentials, raw session tokens, and unnecessary private content.

Operational logs must be access-controlled and given an explicit retention policy before production use.

## Production gates

Before any public deployment, verify TLS, firewall policy, minimal ports, SSH hardening, non-root service execution, database isolation, backups, restore, cookie security, rate limiting, dependency review, monitoring, alerting, log retention, credential rotation, and incident response.

None of those host-level controls is currently verified.
