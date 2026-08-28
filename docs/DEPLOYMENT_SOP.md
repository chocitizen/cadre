# LANSEIR Deployment SOP

## Gate order

1. Verify the canonical repository owner, exact repository name, default branch,
   and remote access. Never create or repoint a repository to resolve ambiguity.
2. Preserve the pre-change commit and the complete non-secret working state.
3. Run foundation integrity, tests, static typing, dependency integrity,
   application import, JavaScript syntax, operations tests, and secret/path scans.
4. Commit only reviewed source, policy, tests, and documentation. Exclude local
   credentials, databases, caches, reports, packages, and private production data.
5. Push the exact candidate commit and independently confirm the remote branch resolves to it.
6. Deploy the candidate to Railway staging under `docs/RAILWAY_STAGING_SOP.md`.
7. Record and verify the responsive staging URL without promoting production.
8. After protected-main approval, require the governed controller to fetch that exact SHA from canonical `main`.
9. Validate container health and the release ID before switching live traffic.
10. Confirm approved LANSEIR product routes work over HTTPS and internal/admin
    paths are not public.
11. Provision the allowlisted owner through the governed bootstrap or promotion
    mechanism without emitting credentials; verify live sign-in and the
    protected command surface against the deployed environment.
12. Validate one critical owner journey and capture the exact HTTPS login URL
    and owner email. Deliver credentials only through an approved secure channel.
13. Verify backup, archive integrity, isolated restore, audit chain, and security
    acceptance. Record live evidence; repository tests are not deployment proof.

## READY gate

Deployment status is `NOT_READY` unless every applicable gate passes:

- production build successful;
- production environment configured;
- public HTTPS endpoint resolved;
- required database/services operational;
- owner account provisioned;
- authentication verified against production;
- protected interface smoke-tested;
- critical user journey validated;
- exact login URL and owner identity captured;
- credential delivery approved and secure; and
- rollback available.

Compilation, image build, container startup, health, or staging success alone
never satisfies `READY`. `app.services.deployment.assess_production_readiness`
is the executable fail-closed policy.

## Rollback

The controller may report rolled back only after the prior immutable release is
restored and passes release-bound health. Otherwise it records
`RECOVERY_REQUIRED`. Never delete a failed release before incident evidence and
its replacement are preserved.

## Current external dependencies

GitHub publication requires authenticated access to the configured canonical
repository and protected-main approval. Railway staging requires the CLI,
project binding, runtime credential, environment configuration, and live URL
acceptance. Hostinger activation requires verified VPS access, DNS, TLS, firewall,
root-owned policy installation, production secrets, and live acceptance.
LiteLLM/OpenRouter activation requires a healthy internal gateway, server-side
credentials, explicit routing policy, provider provenance, and failure-path tests.
