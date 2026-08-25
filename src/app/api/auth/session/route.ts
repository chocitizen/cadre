import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { authenticateApiRequest } from "@/server/auth/request";
import { handleApiError, requestId } from "@/server/http";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  const correlationId = requestId(request);

  try {
    const { session, user } = await authenticateApiRequest(request);
    return NextResponse.json(
      {
        authenticated: true as const,
        session: { absoluteExpiresAt: session.absoluteExpiresAt.toISOString() },
        user: {
          id: user.id,
          displayName: user.displayName,
          email: user.email,
          role: user.role
        }
      },
      { headers: { "Cache-Control": "no-store", "X-Request-Id": correlationId } }
    );
  } catch (cause) {
    const response = handleApiError(cause);
    response.headers.set("Cache-Control", "no-store");
    response.headers.set("X-Request-Id", correlationId);
    return response;
  }
}
