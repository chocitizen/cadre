# LANSEIR Deployment SOP

## Gate order

1. Verify the canonical repository owner, exact repository name, default branch,
   and remote access. Never create or repoint a repository to resolve ambiguity.
2. Preserve the pre-change commit and the complete non-secret working state.
3. Run foundation integrity, tests, static typing, dependency integrity,
   application import, JavaScript syntax, operations tests, and secret/path scans.
4. Commit only reviewed source, policy, tests, and documentation. Exclude local
   credentials, databases, caches, reports, packages, and private production data.
5. Push the exact commit and independently confirm remote `main` resolves to it.
6. Require the governed controller to fetch that exact SHA from canonical `main`.
7. Validate container health and the release ID before switching live traffic.
8. Confirm approved LANSEIR product routes work over HTTPS and internal/admin
   paths are not public.
9. Verify backup, archive integrity, isolated restore, audit chain, and security
   acceptance. Record live evidence; repository tests are not deployment proof.

## Rollback

The controller may report rolled back only after the prior immutable release is
restored and passes release-bound health. Otherwise it records
`RECOVERY_REQUIRED`. Never delete a failed release before incident evidence and
its replacement are preserved.

## Current external dependencies

GitHub publication requires a visible, accessible repository named exactly
`lanseir`. Hostinger activation requires verified VPS access, DNS, TLS, firewall,
root-owned policy installation, production secrets, and live acceptance.
LiteLLM/OpenRouter activation requires a healthy internal gateway, server-side
credentials, explicit routing policy, provider provenance, and failure-path tests.
