import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import type { ArtifactSummary } from "@/lib/types";
import { getMarkdownArtifact, type MarkdownArtifactRecord } from "@/server/artifacts/service";
import { authenticateApiRequest } from "@/server/auth/request";
import { getAuthorizedArtifact } from "@/server/data";
import { getDatabase } from "@/server/db";
import { handleApiError, HttpError, requestId } from "@/server/http";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const artifactIdSchema = z.string().uuid();

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

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ artifactId: string }> }
) {
  const correlationId = requestId(request);

  try {
    const parsedId = artifactIdSchema.safeParse((await context.params).artifactId);
    if (!parsedId.success) {
      throw new HttpError(404, "not_found", "Artifact was not found.");
    }

    const db = await getDatabase();
    const { user } = await authenticateApiRequest(request, { database: db });
    const authorizedArtifact = await getAuthorizedArtifact(db, user.id, parsedId.data);
    if (!authorizedArtifact || authorizedArtifact.type !== "markdown") {
      throw new HttpError(404, "not_found", "Artifact was not found.");
    }

    const record = await getMarkdownArtifact(authorizedArtifact.workspaceId, parsedId.data);
    if (!record) {
      throw new HttpError(404, "not_found", "Artifact was not found.");
    }

    return withResponseHeaders(
      NextResponse.json({ artifact: toArtifactSummary(record) }),
      correlationId
    );
  } catch (cause) {
    return withResponseHeaders(handleApiError(cause), correlationId);
  }
}
