import { createHash } from "node:crypto";

import { eq, sql } from "drizzle-orm";

import type { CadreDatabase } from "../db/client";
import { authThrottles } from "../db/schema";

export const LOGIN_ATTEMPT_LIMIT = 5;
export const LOGIN_WINDOW_MS = 15 * 60 * 1000;
export const LOGIN_BLOCK_MS = 15 * 60 * 1000;

/**
 * Produces the only form of a login identifier permitted in the throttle table.
 * The domain separator prevents reuse of the digest as a general email fingerprint.
 */
export function hashLoginIdentifier(normalizedEmail: string): string {
  return createHash("sha256").update(`cadre:login:${normalizedEmail}`, "utf8").digest("hex");
}

export async function isLoginBlocked(
  db: CadreDatabase,
  normalizedEmail: string,
  now = new Date()
): Promise<boolean> {
  const [record] = await db
    .select({ blockedUntil: authThrottles.blockedUntil })
    .from(authThrottles)
    .where(eq(authThrottles.identifierHash, hashLoginIdentifier(normalizedEmail)))
    .limit(1);

  return Boolean(record?.blockedUntil && record.blockedUntil.getTime() > now.getTime());
}

/**
 * Atomically increments a failed-attempt window so concurrent failures cannot
 * overwrite one another with a lower count.
 */
export async function recordLoginFailure(
  db: CadreDatabase,
  normalizedEmail: string,
  now = new Date()
): Promise<void> {
  const identifierHash = hashLoginIdentifier(normalizedEmail);
  const windowCutoff = new Date(now.getTime() - LOGIN_WINDOW_MS);
  const blockedUntil = new Date(now.getTime() + LOGIN_BLOCK_MS);
  const windowExpired = sql`${authThrottles.windowStartedAt} <= ${windowCutoff}`;

  await db
    .insert(authThrottles)
    .values({
      identifierHash,
      attemptCount: 1,
      windowStartedAt: now,
      blockedUntil: null,
      updatedAt: now
    })
    .onConflictDoUpdate({
      target: authThrottles.identifierHash,
      set: {
        attemptCount: sql<number>`case when ${windowExpired} then 1 else ${authThrottles.attemptCount} + 1 end`,
        windowStartedAt: sql<Date>`case when ${windowExpired} then ${now} else ${authThrottles.windowStartedAt} end`,
        blockedUntil: sql<Date | null>`case
          when ${windowExpired} then null::timestamptz
          when ${authThrottles.attemptCount} + 1 >= ${LOGIN_ATTEMPT_LIMIT} then ${blockedUntil}::timestamptz
          else null::timestamptz
        end`,
        updatedAt: now
      }
    });
}

export async function clearLoginFailures(
  db: CadreDatabase,
  normalizedEmail: string
): Promise<void> {
  await db
    .delete(authThrottles)
    .where(eq(authThrottles.identifierHash, hashLoginIdentifier(normalizedEmail)));
}
