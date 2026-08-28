# External Dependency Packet

Only owner, provider, or live-host actions remain here.

## 1. Hostinger production activation

**WHAT IS REQUIRED**
An authenticated Hostinger VPS session, the real public hostname, ACME email,
root-owned 0600 production secret file, and permission to deploy the committed
exact `main` SHA.

**WHY IT IS REQUIRED**
This workstation has no Docker and no VPS session; repository evidence cannot
prove container build, firewall, HTTPS, listeners, backups, or rollback.

**WHERE TO OBTAIN IT**
The LANSEIR Hostinger owner account, DNS provider, and approved password/token
generator.

**WHERE IT GOES**
Values follow `ops/config/cadre.env.example` and install as
`/opt/lanseir/secrets/cadre.env` with root ownership and mode 0600. Do not send
secrets through chat or commit them.

**HOW TO VERIFY IT**
Follow `docs/HOSTINGER_OPERATIONS_RUNBOOK.md`, including security audit,
deploy, release-bound health, public-route, backup, restore-test, restart, and
rollback evidence.

**WHAT WILL ACTIVATE AFTERWARD**
The public LANSEIR product, persistent PostgreSQL runtime, HTTPS, scheduled
health checks/backups, and governed production releases.

## 2. Authorized VESSEL source promotion

**WHAT IS REQUIRED**
The exact current Sirrah Publishing manuscript/audio masters, provenance, and
explicit approval to ingest and publish them.

**WHY IT IS REQUIRED**
Protected intellectual property cannot be approximated or inferred. The
product mechanics are ready; content remains `draft`.

**WHERE TO OBTAIN IT**
The governing Source of Truth Registry and designated Sirrah Publishing
custodian.

**WHERE IT GOES**
Approved chapter/audio records are inserted through the administrator content
boundary; binary assets go to an approved private object store, not Git.

**HOW TO VERIFY IT**
Match source hashes/provenance, confirm chapter order and media integrity, then
grant a test entitlement and validate read/listen/resume before publication.

**WHAT WILL ACTIVATE AFTERWARD**
VESSEL reading, authorized notes/bookmarks, and optional audiobook playback.

## 3. Identity email delivery

**WHAT IS REQUIRED**
Owner selection and approval of a transactional email provider, sending domain,
verified sender, destination policy, and credential custody.

**WHY IT IS REQUIRED**
Verification/reset tokens are generated securely, but transmitting them to an
unspecified external destination would expose credentials without authority.

**WHERE TO OBTAIN IT**
The approved provider account and DNS owner.

**WHERE IT GOES**
Provider credentials stay server-side in the root-owned production secret
boundary after a destination-specific adapter is reviewed.

**HOW TO VERIFY IT**
Create an account, receive and redeem verification, request and redeem one
password reset, confirm expiry/single use, and confirm reset revokes sessions.

**WHAT WILL ACTIVATE AFTERWARD**
Production email verification and self-service password recovery.

## 4. Production governance decisions

**WHAT IS REQUIRED**
Formal legal review of Terms/Privacy; an encrypted off-server backup destination;
a Griot-controlled external audit-head anchor; and payment-provider approval if
commercial entitlements are enabled.

**WHY IT IS REQUIRED**
These require legal authority, external custody, or financial authorization.

**WHERE TO OBTAIN IT**
Qualified counsel and the owner-approved backup, audit, and payment providers.

**WHERE IT GOES**
Provider-specific production policy and secrets, outside Git.

**HOW TO VERIFY IT**
Record legal approval; perform an off-server restore drill; verify an external
audit head/count; and test signed payment webhooks independently from product
entitlements.

**WHAT WILL ACTIVATE AFTERWARD**
Legally approved public policy, disaster recovery beyond the VPS, root-resistant
audit continuity, and provider-backed commercial access.

Paid remote AI is optional: the local Reflection Guide is operational. If a
premium provider is desired, explicit cost authorization and a server-side key
activate the existing OpenAI-compatible adapter.
