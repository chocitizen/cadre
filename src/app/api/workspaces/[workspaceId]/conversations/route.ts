import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import type { ConversationSummary } from "@/lib/types";
import { writeAuditEvent } from "@/server/audit/write";
import { requireWorkspaceAccess } from "@/server/auth";
import { authenticateApiRequest } from "@/server/auth/request";
import { listWorkspaceConversations } from "@/server/data";
import { conversations, getDatabase } from "@/server/db";
import { handleApiError, HttpError, parseJson, requestId } from "@/server/http";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const workspaceIdSchema = z.string().uuid();
const createConversationSchema = z
  .object({
    title: z.string().trim().max(120).optional()
  })
  .strict();

const WRITER_ROLES = ["owner", "admin", "member"] as const;

function parseWorkspaceId(value: string): string {
  const parsed = workspaceIdSchema.safeParse(value);
  if (!parsed.success) {
    throw new HttpError(404, "not_found", "Workspace was not found.");
  }
  return parsed.data;
}

function toConversationSummary(
  conversation: typeof conversations.$inferSelect
): ConversationSummary {
  return {
    id: conversation.id,
    workspaceId: conversation.workspaceId,
    title: conversation.title,
    status: conversation.status,
    provider: conversation.provider,
    model: conversation.model,
    createdAt: conversation.createdAt.toISOString(),
    updatedAt: conversation.updatedAt.toISOString()
  };
}

function withResponseHeaders(response: NextResponse, correlationId: string): NextResponse {
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("X-Request-Id", correlationId);
  return response;
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ workspaceId: string }> }
) {
  const correlationId = requestId(request);

  try {
    const workspaceId = parseWorkspaceId((await context.params).workspaceId);
    const db = await getDatabase();
    const { user } = await authenticateApiRequest(request, { database: db });
    await requireWorkspaceAccess(db, user.id, workspaceId);
    const results = await listWorkspaceConversations(db, workspaceId);

    return withResponseHeaders(NextResponse.json({ conversations: results }), correlationId);
  } catch (cause) {
    return withResponseHeaders(handleApiError(cause), correlationId);
  }
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ workspaceId: string }> }
) {
  const correlationId = requestId(request);

  try {
    const workspaceId = parseWorkspaceId((await context.params).workspaceId);
    const db = await getDatabase();
    const { user } = await authenticateApiRequest(request, { mutation: true, database: db });
    await requireWorkspaceAccess(db, user.id, workspaceId, WRITER_ROLES);
    const input = await parseJson(request, createConversationSchema);

    const [created] = await db
      .insert(conversations)
      .values({
        workspaceId,
        createdByUserId: user.id,
        title: input.title || "Untitled conversation"
      })
      .returning();

    if (!created) {
      throw new Error("The conversation was not persisted.");
    }

    await writeAuditEvent({
      actorUserId: user.id,
      workspaceId,
      eventType: "conversation.created",
      targetType: "conversation",
      targetId: created.id,
      requestId: correlationId
    });

    return withResponseHeaders(
      NextResponse.json({ conversation: toConversationSummary(created) }, { status: 201 }),
      correlationId
    );
  } catch (cause) {
    return withResponseHeaders(handleApiError(cause), correlationId);
  }
}
