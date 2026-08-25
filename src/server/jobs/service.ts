import { and, desc, eq } from "drizzle-orm";

import { writeAuditEvent } from "../audit/write";
import { getDatabase } from "../db/client";
import { jobs, type Job } from "../db/schema";
import { assertJobTransition, isJobState, type JobState } from "./states";

export interface CreateJobInput {
  readonly workspaceId: string;
  readonly conversationId?: string | null;
  readonly requestedByUserId: string;
  readonly operation: string;
  readonly inputMetadata?: Record<string, unknown> | null;
  readonly idempotencyKey?: string | null;
  readonly surfaceInReadyDock?: boolean;
  readonly requestId?: string | null;
}

export interface TransitionJobInput {
  readonly jobId: string;
  readonly workspaceId: string;
  readonly actorUserId: string;
  readonly nextState: JobState;
  readonly progress?: number;
  readonly outputMetadata?: Record<string, unknown> | null;
  readonly errorCode?: string | null;
  readonly errorMessage?: string | null;
  readonly requestId?: string | null;
}

function assertProgress(progress: number): void {
  if (!Number.isInteger(progress) || progress < 0 || progress > 100) {
    throw new Error("Job progress must be an integer from 0 through 100.");
  }
}

export async function createJob(input: CreateJobInput): Promise<Job> {
  const operation = input.operation.trim();
  const idempotencyKey = input.idempotencyKey?.trim() || null;

  if (!operation) {
    throw new Error("A job operation is required.");
  }

  const db = await getDatabase();

  if (idempotencyKey) {
    const [existingJob] = await db
      .select()
      .from(jobs)
      .where(and(eq(jobs.workspaceId, input.workspaceId), eq(jobs.idempotencyKey, idempotencyKey)))
      .limit(1);

    if (existingJob) {
      return existingJob;
    }
  }

  const [createdJob] = await db
    .insert(jobs)
    .values({
      workspaceId: input.workspaceId,
      conversationId: input.conversationId ?? null,
      requestedByUserId: input.requestedByUserId,
      operation,
      executionMode: "inline",
      status: "queued",
      progress: 0,
      inputMetadata: input.inputMetadata ?? null,
      idempotencyKey,
      surfaceInReadyDock: input.surfaceInReadyDock ?? false
    })
    .returning();

  if (!createdJob) {
    throw new Error("The job was not persisted.");
  }

  await writeAuditEvent({
    actorUserId: input.requestedByUserId,
    workspaceId: input.workspaceId,
    eventType: "job.created",
    targetType: "job",
    targetId: createdJob.id,
    requestId: input.requestId,
    metadata: { state: "queued", executionMode: "inline" }
  });

  return createdJob;
}

export async function getJob(workspaceId: string, jobId: string): Promise<Job | null> {
  const db = await getDatabase();
  const [job] = await db
    .select()
    .from(jobs)
    .where(and(eq(jobs.id, jobId), eq(jobs.workspaceId, workspaceId)))
    .limit(1);

  return job ?? null;
}

export async function listJobs(workspaceId: string, limit = 50): Promise<Job[]> {
  const db = await getDatabase();
  return db
    .select()
    .from(jobs)
    .where(eq(jobs.workspaceId, workspaceId))
    .orderBy(desc(jobs.createdAt))
    .limit(Math.min(Math.max(limit, 1), 100));
}

export async function transitionJob(input: TransitionJobInput): Promise<Job> {
  const currentJob = await getJob(input.workspaceId, input.jobId);

  if (!currentJob || !isJobState(currentJob.status)) {
    throw new Error("The job is unavailable.");
  }

  assertJobTransition(currentJob.status, input.nextState);

  const progress =
    input.progress ??
    (input.nextState === "ready" || input.nextState === "delivered"
      ? 100
      : input.nextState === "queued"
        ? 0
        : currentJob.progress);
  assertProgress(progress);

  if (input.nextState === "failed" && (!input.errorCode?.trim() || !input.errorMessage?.trim())) {
    throw new Error("Failed jobs require a safe error code and message.");
  }

  const now = new Date();
  const isComplete = ["ready", "failed", "delivered", "archived"].includes(input.nextState);
  const db = await getDatabase();
  const [updatedJob] = await db
    .update(jobs)
    .set({
      status: input.nextState,
      progress,
      outputMetadata: input.outputMetadata ?? currentJob.outputMetadata,
      errorCode: input.nextState === "failed" ? input.errorCode?.trim() : null,
      errorMessage: input.nextState === "failed" ? input.errorMessage?.trim() : null,
      startedAt:
        input.nextState === "running" ? (currentJob.startedAt ?? now) : currentJob.startedAt,
      completedAt:
        input.nextState === "queued"
          ? null
          : isComplete
            ? (currentJob.completedAt ?? now)
            : currentJob.completedAt,
      updatedAt: now
    })
    .where(
      and(
        eq(jobs.id, input.jobId),
        eq(jobs.workspaceId, input.workspaceId),
        eq(jobs.status, currentJob.status)
      )
    )
    .returning();

  if (!updatedJob) {
    throw new Error("The job changed concurrently; reload it before retrying.");
  }

  await writeAuditEvent({
    actorUserId: input.actorUserId,
    workspaceId: input.workspaceId,
    eventType: "job.state_changed",
    targetType: "job",
    targetId: updatedJob.id,
    requestId: input.requestId,
    metadata: {
      fromState: currentJob.status,
      toState: updatedJob.status,
      progress: updatedJob.progress
    }
  });

  return updatedJob;
}
