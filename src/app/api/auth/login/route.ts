import { eq } from "drizzle-orm";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { z } from "zod";

import {
  assertSameOrigin,
  clearLoginFailures,
  createSession,
  getSessionCookieName,
  getSessionCookieOptions,
  isLoginBlocked,
  normalizeEmail,
  recordLoginFailure,
  revokeSession,
  verifyPassword
} from "@/server/auth";
import { MAXIMUM_PASSWORD_BYTES } from "@/server/auth/password";
import { getDatabase, users } from "@/server/db";
import { handleApiError, HttpError, parseJson, requestId } from "@/server/http";
import { writeAuditEvent } from "@/server/audit/write";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const loginSchema = z
  .object({
    email: z.string().trim().min(3).max(320).email(),
    password: z
      .string()
      .min(1)
      .refine((value) => Buffer.byteLength(value, "utf8") <= MAXIMUM_PASSWORD_BYTES)
  })
  .strict();

// A non-account scrypt hash keeps unknown-account verification on the same work factor.
const DUMMY_PASSWORD_HASH =
  "scrypt$65536$8$2$Y2FkcmUtZHVtbXktc2FsdA$9CDKqXmr1cnCmBXp5bmtaFP4kWBmtmrNEwjwFDhPgqM";

function authenticationFailure(status = 401): HttpError {
  return new HttpError(
    status,
    "authentication_failed",
    status === 429
      ? "Sign-in could not be completed. Try again later."
      : "Sign-in could not be completed."
  );
}

export async function POST(request: NextRequest) {
  const correlationId = requestId(request);

  try {
    assertSameOrigin(request, process.env.APP_URL);
    const input = await parseJson(request, loginSchema);
    const email = normalizeEmail(input.email);
    const db = await getDatabase();

    if (await isLoginBlocked(db, email)) {
      await writeAuditEvent({
        eventType: "auth.login",
        outcome: "denied",
        requestId: correlationId,
        metadata: { reason: "temporarily_unavailable" }
      });
      throw authenticationFailure(429);
    }

    const [user] = await db.select().from(users).where(eq(users.email, email)).limit(1);
    const passwordHash = user?.passwordHash ?? DUMMY_PASSWORD_HASH;
    const passwordAccepted = await verifyPassword(input.password, passwordHash);

    if (!user || user.status !== "active" || !passwordAccepted) {
      await recordLoginFailure(db, email);
      await writeAuditEvent({
        eventType: "auth.login",
        outcome: "failure",
        requestId: correlationId,
        metadata: { reason: "credential_rejected" }
      });
      throw authenticationFailure();
    }

    const createdSession = await createSession(db, user.id, {
      userAgent: request.headers.get("user-agent") ?? undefined
    });

    try {
      const now = new Date();
      await db.update(users).set({ lastLoginAt: now, updatedAt: now }).where(eq(users.id, user.id));
      await clearLoginFailures(db, email);
      await writeAuditEvent({
        actorUserId: user.id,
        eventType: "auth.login",
        targetType: "session",
        targetId: createdSession.session.id,
        outcome: "success",
        requestId: correlationId
      });
    } catch (cause) {
      await revokeSession(db, createdSession.token).catch(() => undefined);
      throw cause;
    }

    const cookieOptions = getSessionCookieOptions();
    const response = NextResponse.json(
      { authenticated: true as const },
      { headers: { "Cache-Control": "no-store", "X-Request-Id": correlationId } }
    );
    response.cookies.set(getSessionCookieName(), createdSession.token, cookieOptions);
    response.cookies.set("cadre_csrf", createdSession.csrfToken, {
      ...cookieOptions,
      httpOnly: false
    });
    return response;
  } catch (cause) {
    const response = handleApiError(cause);
    response.headers.set("Cache-Control", "no-store");
    response.headers.set("X-Request-Id", correlationId);
    return response;
  }
}
