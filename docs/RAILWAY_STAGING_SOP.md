# Railway Staging SOP

Railway is the preview/staging target, not automatic production authority.

## Eligibility gate

Before a deploy mission is approved, Al records:

1. canonical repository and application root;
2. exact commit SHA and rollback reference;
3. detected framework/runtime;
4. verified build and start commands;
5. port binding and health-check path;
6. required environment-variable names, with values stored outside Git;
7. test, lint, type, build, and secret-scan results; and
8. acceptance criteria for HTTP and responsive rendering.

## Adapter gate

`DEPLOY` discovers `railway.staging.deploy`. Dispatch is blocked unless the
runtime proves the Railway CLI, staging project identifier, and service
credential. The credential is never returned or persisted by the gateway.

## Deployment and validation

The approved mission must deploy the exact validated commit, wait for service
health, verify a successful HTTP response, inspect responsive rendering at
mobile/tablet/desktop widths, capture the staging URL, record the Railway
deployment identifier, and attach evidence to the mission. A URL without HTTP
and rendering verification is not a completed staging deployment.

Railway staging never promotes itself to Hostinger production. Production
promotion is a separate approved mission using the Hostinger operations policy,
release-bound health, backup, and rollback acceptance.

## Failure

On failure, record the build/runtime output in the protected evidence store,
sanitize provider output, preserve the last known good deployment, and return
the exact blocker and resume command `DEPLOY`. Never loop paid deployments after
an authorization, configuration, or deterministic build failure.
