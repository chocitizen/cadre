# LANSEIR Autonomous Mission Execution Standard

## Authority and scope

LANSEIR is the sovereign parent. CADRE is the internal execution system.
Mission Control may route only approved Command Briefs to active specialists.
Specialists remain bounded by their registered permissions, dependencies,
validation requirements, and service identities.

## Canonical execution sequence

1. Translate an approved Command Brief into bounded missions with named outputs,
   validation criteria, dependencies, priority, and a retry ceiling.
2. Dispatch the highest-priority mission whose dependencies are verified.
3. Record the real specialist run as dispatched/running; do not manufacture a
   result summary before work exists.
4. Attach material evidence. Accepted classes include created artifacts,
   committed code, passed tests, completed deployment, resolved dependency,
   passed verification, captured failure, diagnosis, repair, archive, and cleanup.
5. Move a mission to verification pending only after material evidence exists.
6. A Griot or Mission Control verifier records `verification_passed` and then
   promotes the mission to verified.
7. Complete the Command Brief only when every mission is verified.
8. Dispatch the next dependency-ready mission automatically.

“Still working,” “in progress,” “ongoing,” “continuing,” and equivalent status
messages are rejected as evidence. A dashboard count or agent claim is not proof.

## Failure and FIX

Failed, blocked, stalled, and verification-failed missions expose FIX. A
deterministic failure creates an Al recovery mission and dispatches it before
the original work can retry. Recovery requires diagnosis, repair evidence, and
passed verification. A verified recovery may resume the original mission only
within its retry ceiling. Authorization, policy, and unresolved dependency
failures remain blocked rather than being bypassed.

## Completion contract

The execution record must separate queued, dispatched, running, verification
pending, verified, failed, blocked, stalled, verification failed, recovering,
and cancelled. “Complete” means evidence exists, validation passed, and the
authorized verifier accepted the result. Local validation, GitHub publication,
deployment, and live production acceptance are separate facts.
