import { and, eq } from "drizzle-orm";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import type { ArtifactSummary } from "@/lib/types";
import {
  createMarkdownArtifact,
  getMarkdownArtifact,
  type MarkdownArtifactRecord
} from "@/server/artifacts/service";
import { authenticateApiRequest } from "@/server/auth/request";
import {
  artifacts,
  conversations,
  getDatabase,
  messages,
  notifications,
  workspaceMemberships,
  workspaces,
  type Job
} from "@/server/db";
import { handleApiError, HttpError, parseJson, requestId } from "@/server/http";
import { createJob, transitionJob, type CreateJobInput } from "@/server/jobs/service";
import { createNotification } from "@/server/notifications/service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const createArtifactSchema = z
  .object({
    conversationId: z.string().uuid(),
    messageId: z.string().uuid(),
    title: z.string().trim().min(1).max(200)
  })
  .strict();

function toArtifactSummary(record: MarkdownArtifactRecord): ArtifactSummary {
  return {
    id: record.artifact.id,
    workspaceId: record.artifact.workspaceId,
    conversationId: record.artifact.conversationId,
    jobId: record.artifact.sourceJobId,
    title: record.artifact.title,
    type: record.artifact.kind,
    currentVersion: record.artifact.currentVersion,
    approvalState: record.artifact.approvalState,
    checksum: record.version.checksumSha256,
    content: record.version.contentText ?? undefined,
    createdAt: record.artifact.createdAt.toISOString(),
    updatedAt: record.artifact.updatedAt.toISOString()
  };
}

function withResponseHeaders(response: NextResponse, correlationId: string): NextResponse {
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("X-Request-Id", correlationId);
  return response;
}

async function loadExistingArtifact(
  workspaceId: string,
  sourceJobId: string
): Promise<MarkdownArtifactRecord | null> {
  const db = await getDatabase();
  const [existing] = await db
    .select({ id: artifacts.id })
    .from(artifacts)
    .where(
      and(
        eq(artifacts.workspaceId, workspaceId),
        eq(artifacts.sourceJobId, sourceJobId),
        eq(artifacts.kind, "markdown")
      )
    )
    .limit(1);

  return existing ? getMarkdownArtifact(workspaceId, existing.id) : null;
}

export async function POST(request: NextRequest) {
  const correlationId = requestId(request);
  let activeJob: Job | null = null;
  let ownsRunningJob = false;

  try {
    const db = await getDatabase();
    const { user } = await authenticateApiRequest(request, { mutation: true, database: db });
    const input = await parseJson(request, createArtifactSchema);
    const [authorizedSource] = await db
      .select({
        workspaceId: conversations.workspaceId,
        content: messages.contentText,
        provider: messages.provider,
        model: messages.model,
        promptVersion: messages.promptVersion,
        membershipRole: workspaceMemberships.role
      })
      .from(messages)
      .innerJoin(
        conversations,
        and(
          eq(conversations.id, messages.conversationId),
          eq(conversations.workspaceId, messages.workspaceId),
          eq(conversations.status, "active")
        )
      )
      .innerJoin(
        workspaces,
        and(eq(workspaces.id, conversations.workspaceId), eq(workspaces.status, "active"))
      )
      .innerJoin(
        workspaceMemberships,
        and(
          eq(workspaceMemberships.workspaceId, conversations.workspaceId),
          eq(workspaceMemberships.userId, user.id)
        )
      )
      .where(
        and(
          eq(messages.id, input.messageId),
          eq(messages.conversationId, input.conversationId),
          eq(messages.role, "assistant"),
          eq(messages.status, "completed")
        )
      )
      .limit(1);

    if (!authorizedSource || authorizedSource.membershipRole === "viewer") {
      throw new HttpError(404, "not_found", "The source message was not found.");
    }

    const jobInput: CreateJobInput = {
      workspaceId: authorizedSource.workspaceId,
      conversationId: input.conversationId,
      requestedByUserId: user.id,
      operation: "artifact.markdown.create",
      inputMetadata: { sourceMessageId: input.messageId },
      idempotencyKey: `markdown-message:${input.messageId}`,
      surfaceInReadyDock: true,
      requestId: correlationId
    };
    let job = await createJob(jobInput);
    activeJob = job;
    let artifact = await loadExistingArtifact(authorizedSource.workspaceId, job.id);

    if (!artifact && job.status === "running") {
      throw new HttpError(
        409,
        "artifact_in_progress",
        "This Markdown artifact is already being prepared."
      );
    }

    if (job.status === "failed") {
      job = await transitionJob({
        jobId: job.id,
        workspaceId: authorizedSource.workspaceId,
        actorUserId: user.id,
        nextState: "queued",
        progress: 0,
        requestId: correlationId
      });
      activeJob = job;
    }

    if (job.status === "queued") {
      job = await transitionJob({
        jobId: job.id,
        workspaceId: authorizedSource.workspaceId,
        actorUserId: user.id,
        nextState: "running",
        progress: 20,
        requestId: correlationId
      });
      activeJob = job;
      ownsRunningJob = true;
    }

    if (!artifact) {
      if (job.status !== "running") {
        throw new HttpError(
          409,
          "artifact_unavailable",
          "This Markdown artifact cannot be created in its current state."
        );
      }

      artifact = await createMarkdownArtifact({
        workspaceId: authorizedSource.workspaceId,
        conversationId: input.conversationId,
        sourceJobId: job.id,
        createdByUserId: user.id,
        title: input.title,
        markdown: authorizedSource.content,
        provenance: {
          source: "conversation",
          sourceId: input.messageId,
          providerId: authorizedSource.provider ?? undefined,
          model: authorizedSource.model ?? undefined,
          promptVersion:
            authorizedSource.promptVersion === null
              ? undefined
              : String(authorizedSource.promptVersion),
          canonicalStatus: "working",
          metadata: { conversationId: input.conversationId }
        },
        approvalState: "draft",
        requestId: correlationId
      });
    }

    const actionPath = `/app/artifacts/${artifact.artifact.id}`;
    const [existingNotification] = await db
      .select({ id: notifications.id })
      .from(notifications)
      .where(
        and(
          eq(notifications.userId, user.id),
          eq(notifications.workspaceId, authorizedSource.workspaceId),
          eq(notifications.jobId, job.id),
          eq(notifications.artifactId, artifact.artifact.id)
        )
      )
      .limit(1);

    if (!existingNotification) {
      await createNotification({
        userId: user.id,
        workspaceId: authorizedSource.workspaceId,
        jobId: job.id,
        artifactId: artifact.artifact.id,
        type: "artifact.ready",
        title: artifact.artifact.title,
        body: "A governed Markdown artifact is ready for review.",
        actionPath
      });
    }

    if (job.status === "running" || job.status === "review") {
      job = await transitionJob({
        jobId: job.id,
        workspaceId: authorizedSource.workspaceId,
        actorUserId: user.id,
        nextState: "ready",
        progress: 100,
        outputMetadata: {
          artifactId: artifact.artifact.id,
          artifactVersion: artifact.artifact.currentVersion
        },
        requestId: correlationId
      });
      activeJob = job;
    }

    if (job.status !== "ready" && job.status !== "delivered") {
      throw new HttpError(
        409,
        "artifact_unavailable",
        "This Markdown artifact is not ready for delivery."
      );
    }

    return withResponseHeaders(
      NextResponse.json(
        { artifact: toArtifactSummary(artifact), readyDock: { actionPath } },
        { status: 201 }
      ),
      correlationId
    );
  } catch (cause) {
    if (ownsRunningJob && activeJob?.status === "running") {
      await transitionJob({
        jobId: activeJob.id,
        workspaceId: activeJob.workspaceId,
        actorUserId: activeJob.requestedByUserId,
        nextState: "failed",
        errorCode: "artifact_workflow_failed",
        errorMessage: "The Markdown artifact workflow did not complete.",
        requestId: correlationId
      }).catch(() => undefined);
    }
    return withResponseHeaders(handleApiError(cause), correlationId);
  }
}
