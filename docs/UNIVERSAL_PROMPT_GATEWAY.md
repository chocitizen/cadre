# LANSEIR Universal Prompt Gateway

## Authority and purpose

Every authorized operational interface sends founder requests through
`POST /api/v1/gateway/resolve`. The gateway resolves identity, command meaning,
canonical project state, doctrine, approval state, specialist authority,
available service capability, executable action, evidence, and the next action
before it dispatches work. A short input never lowers the reasoning standard.

The gateway extends the existing Command Brief and Mission Control records. It
does not create a parallel task system. Unrecognized substantive requests become
draft Command Briefs under the active canonical project and remain gated until
explicit approval.

## Command Registry

The executable registry is `app/services/command_registry.py` and is exposed at
`GET /api/v1/gateway/commands`.

| Founder input | Resolved action |
| --- | --- |
| First `SIGNAL` | Dispatch the currently staged approved action. |
| Following `SIGNAL` | Deliver the resulting registered artifact immediately. |
| `NOW`, `GO` | Dispatch the current executable action immediately. |
| `ADVANCE`, `ACT` | Continue the approved workflow. |
| `ACTIVELY ADVANCE` | Move approved work into implementation. |
| `DEPLOY` | Dispatch an approved Railway staging mission only when the adapter proves staging capability. |
| `+` | Approve the exact referenced draft Command Brief. No global approval is inferred. |
| `STATUS` | Return actual state, evidence, blockers, and next action. |
| `YOU KNOW WHAT TO DO` | Resolve state and continue the approved next action. |

Unknown long requests are normalized, routed to specialists, and stored as a
draft Command Brief. The response returns the exact brief identifier needed for
the `+` approval signal.

## Context Resolution SOP

1. Authenticate the service identity; never accept an actor role from request data.
2. Load the versioned execution-state record and select the explicit project or
   the state-designated active project.
3. Retrieve the active/approved Command Brief, dependency-ready mission,
   doctrine registry, canonical source references, and locked assets.
4. Discover adapter capabilities from the runtime. A configured service name is
   never treated as proven access.
5. Assemble a lead specialist, supporting specialists, validation specialist,
   security implications, operational implications, sources, and acceptance criteria.
6. Resolve the approval/lock state before any dispatch.
7. Execute only the bounded action permitted by the command and identity.
8. Persist a gateway receipt, audit event, execution-state revision, blockers,
   artifacts, validation, and next executable action.

## Specialist-Authority Handoff Standard

Al leads engineering, repository, automation, build, test, deployment, and
recovery work. ARC leads model/provider architecture. Invictus leads security
work. Griot leads canonical/provenance work. The resolver adds qualified support
and a validation specialist from the active registry. Inactive or nonexistent
specialists are never presented as assigned.

Handoffs include the resolved intent, canonical sources, constraints, capability
plan, expected outputs, validation criteria, security implications, and the
durable mission/brief identifiers. Mission completion still requires material
evidence and an authorized verification record.

Every substantive response contains an `artifact` object and `copy_ready_note`.
The note is self-contained and includes the objective, governing decisions,
locked constraints, named authorities, sources, implementation and technical
requirements, dependencies, security, preservation, commands/configuration,
validation, acceptance, outputs, reporting, and rollback. When a registered
mission file is due, `SIGNAL` returns its exact locator, SHA-256, state, and
delivery note. Previously delivered artifact identifiers remain in execution
state to prevent silent loss or repeated dispatch.

## Execution State Protocol

`execution_states` is the runtime authority for cross-process current state.
`app/resources/execution_state.default.json` is its version-controlled bootstrap,
not a second live state file. State uses optimistic revisions. Stale writes fail
with `409`; updates to approved decisions, locked assets, or rollback authority
require the Founder service identity.

The context packet at `GET /api/v1/gateway/context` includes active project,
milestone, objective, approved decisions, locked assets, open/completed/blocked
missions, next executable work, assigned agents, deployment and environment
state, service status, doctrine references, validated commit, last deployment,
and rollback reference.

## Context portability boundary

Authorized terminals, coding agents, LANSEIR clients, and automation workers can
consume the context packet and submit gateway requests. Third-party chat or AI
platforms do not receive this state automatically unless their integration calls
the API with an authorized service identity. No claim of universal injection is
made across platforms that do not support that integration.

`interface` records voice, typed, mobile, desktop, command-surface, API,
agent-to-agent, automation, delegated, and future channel provenance.
`operating_mode` distinguishes founder and client operation. Neither field may
degrade routing, completeness, validation, privacy, or delivery.

## Failure response

Blocked responses contain `required_capability`,
`required_permission_or_credential`, `affected_service`,
`exact_human_action_required`, and `resume_command`. The request and state
revision remain durable so the workflow can resume without rediscovery.
