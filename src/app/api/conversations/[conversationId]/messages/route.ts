import { and, eq } from "drizzle-orm";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import type { MessageDto } from "@/lib/types";
import { sendChatMessage } from "@/server/ai/chat-service";
import { writeAuditEvent } from "@/server/audit/write";
import { authenticateApiRequest } from "@/server/auth/request";
import {
  conversations,
  getDatabase,
  workspaceMemberships,
  workspaces,
  type Message
} from "@/server/db";
import { handleApiError, HttpError, parseJson, requestId } from "@/server/http";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const conversationIdSchema = z.string().uuid();
const sendMessageSchema = z
  .object({
    content: z.string().trim().min(1).max(32_000),
    clientRequestId: z.string().uuid().optional()
  })
  .strict();

function toMessageDto(message: Message): MessageDto {
  return {
    id: message.id,
    conversationId: message.conversationId,
    role: message.role as MessageDto["role"],
    content: message.contentText,
    provider: message.provider,
    model: message.model,
    createdAt: message.createdAt.toISOString()
  };
}

function withResponseHeaders(response: NextResponse, correlationId: string): NextResponse {
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("X-Request-Id", correlationId);
  return response;
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ conversationId: string }> }
) {
  const correlationId = requestId(request);

  try {
    const parsedId = conversationIdSchema.safeParse((await context.params).conversationId);
    if (!parsedId.success) {
      throw new HttpError(404, "not_found", "Conversation was not found.");
    }

    const db = await getDatabase();
    const { user } = await authenticateApiRequest(request, { mutation: true, database: db });
    const input = await parseJson(request, sendMessageSchema);
    const [authorizedConversation] = await db
      .select({
        workspaceId: conversations.workspaceId,
        membershipRole: workspaceMemberships.role
      })
      .from(conversations)
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
      .where(and(eq(conversations.id, parsedId.data), eq(conversations.status, "active")))
      .limit(1);

    if (!authorizedConversation || authorizedConversation.membershipRole === "viewer") {
      throw new HttpError(404, "not_found", "Conversation was not found.");
    }

    let result;
    try {
      result = await sendChatMessage({
        conversationId: parsedId.data,
        workspaceId: authorizedConversation.workspaceId,
        userId: user.id,
        content: input.content,
        clientRequestId: input.clientRequestId
      });
    } catch (cause) {
      if (cause instanceof Error && cause.message === "AI response generation failed.") {
        throw new HttpError(
          502,
          "provider_unavailable",
          "CADRE could not complete the AI response. Please retry safely."
        );
      }
      throw cause;
    }

    await writeAuditEvent({
      actorUserId: user.id,
      workspaceId: authorizedConversation.workspaceId,
      eventType: "conversation.message_completed",
      targetType: "conversation",
      targetId: parsedId.data,
      requestId: correlationId,
      metadata: {
        provider: result.generation.providerId,
        model: result.generation.model
      }
    });

    return withResponseHeaders(
      NextResponse.json(
        {
          userMessage: toMessageDto(result.userMessage),
          assistantMessage: toMessageDto(result.assistantMessage)
        },
        { status: 201 }
      ),
      correlationId
    );
  } catch (cause) {
    return withResponseHeaders(handleApiError(cause), correlationId);
  }
}
