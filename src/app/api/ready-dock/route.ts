import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import { authenticateApiRequest } from "@/server/auth/request";
import { listReadyDock } from "@/server/data";
import { getDatabase } from "@/server/db";
import { handleApiError, HttpError, requestId } from "@/server/http";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const querySchema = z
  .object({
    limit: z.coerce.number().int().min(1).max(100).default(50)
  })
  .strict();

function withResponseHeaders(response: NextResponse, correlationId: string): NextResponse {
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("X-Request-Id", correlationId);
  return response;
}

export async function GET(request: NextRequest) {
  const correlationId = requestId(request);

  try {
    const query = querySchema.safeParse({
      limit: request.nextUrl.searchParams.get("limit") ?? undefined
    });
    if (!query.success) {
      throw new HttpError(422, "invalid_request", "The request contains invalid fields.");
    }

    const db = await getDatabase();
    const { user } = await authenticateApiRequest(request, { database: db });
    const items = await listReadyDock(db, user.id, query.data.limit);

    return withResponseHeaders(NextResponse.json({ items }), correlationId);
  } catch (cause) {
    return withResponseHeaders(handleApiError(cause), correlationId);
  }
}
