import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import { authenticateApiRequest } from "@/server/auth/request";
import { getAuthorizedConversation } from "@/server/data";
import { getDatabase } from "@/server/db";
import { handleApiError, HttpError, requestId } from "@/server/http";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const conversationIdSchema = z.string().uuid();

function withResponseHeaders(response: NextResponse, correlationId: string): NextResponse {
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("X-Request-Id", correlationId);
  return response;
}

export async function GET(
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
    const { user } = await authenticateApiRequest(request, { database: db });
    const conversation = await getAuthorizedConversation(db, user.id, parsedId.data);

    if (!conversation) {
      throw new HttpError(404, "not_found", "Conversation was not found.");
    }

    return withResponseHeaders(NextResponse.json(conversation), correlationId);
  } catch (cause) {
    return withResponseHeaders(handleApiError(cause), correlationId);
  }
}
