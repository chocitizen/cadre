import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

import { authenticateApiRequest } from "@/server/auth/request";
import {
  getSessionCookieName,
  getSessionCookieOptions,
  revokeSession
} from "@/server/auth/session";
import { writeAuditEvent } from "@/server/audit/write";
import { getDatabase } from "@/server/db";
import { handleApiError, requestId } from "@/server/http";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  const correlationId = requestId(request);

  try {
    const db = await getDatabase();
    const authenticated = await authenticateApiRequest(request, { mutation: true, database: db });
    const sessionCookieName = getSessionCookieName();
    const sessionToken = request.cookies.get(sessionCookieName)?.value ?? "";

    await revokeSession(db, sessionToken);
    await writeAuditEvent({
      actorUserId: authenticated.user.id,
      eventType: "auth.logout",
      targetType: "session",
      targetId: authenticated.session.id,
      outcome: "success",
      requestId: correlationId
    });

    const response = NextResponse.json(
      { authenticated: false as const },
      { headers: { "Cache-Control": "no-store", "X-Request-Id": correlationId } }
    );
    const cookieOptions = getSessionCookieOptions();
    response.cookies.set(sessionCookieName, "", {
      ...cookieOptions,
      expires: new Date(0),
      maxAge: 0
    });
    response.cookies.set("cadre_csrf", "", {
      ...cookieOptions,
      expires: new Date(0),
      httpOnly: false,
      maxAge: 0
    });
    return response;
  } catch (cause) {
    const response = handleApiError(cause);
    response.headers.set("Cache-Control", "no-store");
    response.headers.set("X-Request-Id", correlationId);
    return response;
  }
}
