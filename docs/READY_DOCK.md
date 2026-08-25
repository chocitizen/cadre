# Ready Dock

## Purpose

Ready Dock gives the owner one durable place to find completed work without reopening an old conversation and asking for the deliverable again.

It is a view over actual persisted jobs, artifacts, and notifications. It must never imply asynchronous work occurred when no worker ran, and it must never equate operational readiness with canonical approval.

## Workflow

```text
Conversation
  -> requested task
  -> durable job record
  -> actual execution and honest state transitions
  -> persisted artifact
  -> notification
  -> Ready Dock row
  -> open exact artifact
```

## Categories

| Category       | Meaning                                                                    |
| -------------- | -------------------------------------------------------------------------- |
| Ready          | A persisted output is available to open.                                   |
| In Progress    | Execution is actually active.                                              |
| Needs Approval | A defined human decision is required.                                      |
| Scheduled      | Execution has a real trigger or schedule; otherwise do not use this state. |
| Failed         | Execution failed and records a safe, redacted error.                       |
| Archived       | Removed from the active surface while retained according to policy.        |

Delivered is a job lifecycle state and may be shown within Ready or history. Review is a validation state and may be shown within Needs Approval. UI labels may group states, but stored state remains precise.

## Minimum record

- title;
- workspace;
- originating conversation;
- job and status;
- artifact, type, and version;
- creation and completion time;
- notification/read state;
- exact open action;
- approve, revise, or archive action when authorized.

## Approval boundary

Approve changes an application approval state only within the user's authority. It does not automatically promote an artifact into the Obsidian Source of Truth Registry. Canonical promotion requires the governed validation and approval process.

## Foundation v0.1

The foundation may execute a request synchronously while persisting the job transitions and final artifact. A real background worker, retry queue, scheduler, and Redis are deferred. The UI must describe this accurately.

## Validation

- A ready row opens the exact persisted artifact.
- Reopening the application preserves the row and artifact.
- Workspace authorization prevents cross-workspace access.
- Failed jobs do not expose secrets or private provider details.
- Approve/revise/archive actions are audited.
- Status is conveyed by text and semantics, not color alone.
