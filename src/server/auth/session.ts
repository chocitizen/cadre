import { createHash, randomBytes } from "node:crypto";

import { and, eq, gt, isNull } from "drizzle-orm";

import type { CadreDatabase } from "../db/client";
import { sessions, users, type Session, type User } from "../db/schema";

const HOUR_MS = 60 * 60 * 1000;
const DAY_MS = 24 * HOUR_MS;
const SESSION_IDLE_TTL_MS = 12 * HOUR_MS;
const SESSION_ABSOLUTE_TTL_MS = 7 * DAY_MS;
const SESSION_TOUCH_INTERVAL_MS = 5 * 60 * 1000;

export const SESSION_COOKIE_NAME = "cadre_session";
export const SECURE_SESSION_COOKIE_NAME = "__Host-cadre_session";

export interface CreatedSession {
  session: Session;
  token: string;
  csrfToken: string;
}

export interface AuthenticatedSession {
  session: Session;
  user: User;
}

export function hashOpaqueToken(token: string): string {
  return createHash("sha256").update(token, "utf8").digest("hex");
}

export function createOpaqueToken(): string {
  return randomBytes(32).toString("base64url");
}

export async function createSession(
  db: CadreDatabase,
  userId: string,
  options: { now?: Date; userAgent?: string } = {}
): Promise<CreatedSession> {
  const now = options.now ?? new Date();
  const absoluteExpiresAt = new Date(now.getTime() + SESSION_ABSOLUTE_TTL_MS);
  const idleExpiresAt = new Date(
    Math.min(now.getTime() + SESSION_IDLE_TTL_MS, absoluteExpiresAt.getTime())
  );
  const token = createOpaqueToken();
  const csrfToken = createOpaqueToken();
  const [session] = await db
    .insert(sessions)
    .values({
      userId,
      tokenHash: hashOpaqueToken(token),
      csrfTokenHash: hashOpaqueToken(csrfToken),
      userAgentHash: options.userAgent ? hashOpaqueToken(options.userAgent) : null,
      createdAt: now,
      lastSeenAt: now,
      idleExpiresAt,
      absoluteExpiresAt
    })
    .returning();

  if (!session) {
    throw new Error("Session creation failed.");
  }

  return { session, token, csrfToken };
}

export async function findActiveSession(
  db: CadreDatabase,
  token: string,
  now = new Date()
): Promise<AuthenticatedSession | null> {
  if (!token) {
    return null;
  }

  const [result] = await db
    .select({ session: sessions, user: users })
    .from(sessions)
    .innerJoin(users, eq(users.id, sessions.userId))
    .where(
      and(
        eq(sessions.tokenHash, hashOpaqueToken(token)),
        isNull(sessions.revokedAt),
        gt(sessions.idleExpiresAt, now),
        gt(sessions.absoluteExpiresAt, now),
        eq(users.status, "active")
      )
    )
    .limit(1);

  if (!result) {
    return null;
  }

  if (now.getTime() - result.session.lastSeenAt.getTime() >= SESSION_TOUCH_INTERVAL_MS) {
    const nextIdleExpiry = new Date(
      Math.min(now.getTime() + SESSION_IDLE_TTL_MS, result.session.absoluteExpiresAt.getTime())
    );
    await db
      .update(sessions)
      .set({ lastSeenAt: now, idleExpiresAt: nextIdleExpiry })
      .where(eq(sessions.id, result.session.id));
    result.session.lastSeenAt = now;
    result.session.idleExpiresAt = nextIdleExpiry;
  }

  return result;
}

export async function revokeSession(
  db: CadreDatabase,
  token: string,
  now = new Date()
): Promise<void> {
  if (!token) return;
  await db
    .update(sessions)
    .set({ revokedAt: now })
    .where(and(eq(sessions.tokenHash, hashOpaqueToken(token)), isNull(sessions.revokedAt)));
}

export async function revokeAllUserSessions(
  db: CadreDatabase,
  userId: string,
  now = new Date()
): Promise<void> {
  await db
    .update(sessions)
    .set({ revokedAt: now })
    .where(and(eq(sessions.userId, userId), isNull(sessions.revokedAt)));
}

export function getSessionCookieName(isProduction = process.env.NODE_ENV === "production"): string {
  return isProduction ? SECURE_SESSION_COOKIE_NAME : SESSION_COOKIE_NAME;
}

export function getSessionCookieOptions(isProduction = process.env.NODE_ENV === "production") {
  return {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax" as const,
    path: "/",
    maxAge: Math.floor(SESSION_ABSOLUTE_TTL_MS / 1000)
  };
}
