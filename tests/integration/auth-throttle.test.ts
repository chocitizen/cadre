import { eq } from "drizzle-orm";
import { afterEach, describe, expect, it } from "vitest";

import {
  LOGIN_ATTEMPT_LIMIT,
  LOGIN_WINDOW_MS,
  clearLoginFailures,
  hashLoginIdentifier,
  isLoginBlocked,
  recordLoginFailure
} from "../../src/server/auth/login-throttle";
import {
  authThrottles,
  createDatabaseClient,
  runMigrations,
  type DatabaseClient
} from "../../src/server/db";

const clients: DatabaseClient[] = [];

async function migratedDatabase(): Promise<DatabaseClient> {
  const client = await createDatabaseClient({ inMemory: true });
  clients.push(client);
  await runMigrations(client);
  return client;
}

afterEach(async () => {
  await Promise.all(clients.splice(0).map((client) => client.close()));
});

describe("login throttling", () => {
  it("persists only a digest and blocks after the configured failure threshold", async () => {
    const client = await migratedDatabase();
    const email = "owner@example.com";
    const now = new Date("2026-08-25T12:00:00.000Z");

    for (let attempt = 0; attempt < LOGIN_ATTEMPT_LIMIT; attempt += 1) {
      await recordLoginFailure(client.db, email, new Date(now.getTime() + attempt));
    }

    const [record] = await client.db
      .select()
      .from(authThrottles)
      .where(eq(authThrottles.identifierHash, hashLoginIdentifier(email)))
      .limit(1);

    expect(record).toMatchObject({
      identifierHash: hashLoginIdentifier(email),
      attemptCount: LOGIN_ATTEMPT_LIMIT
    });
    expect(record?.identifierHash).not.toContain(email);
    await expect(
      isLoginBlocked(client.db, email, new Date(now.getTime() + LOGIN_ATTEMPT_LIMIT))
    ).resolves.toBe(true);
  }, 20_000);

  it("resets an expired window and removes the record after successful authentication", async () => {
    const client = await migratedDatabase();
    const email = "owner@example.com";
    const startedAt = new Date("2026-08-25T12:00:00.000Z");

    await recordLoginFailure(client.db, email, startedAt);
    await recordLoginFailure(client.db, email, new Date(startedAt.getTime() + LOGIN_WINDOW_MS + 1));

    const [record] = await client.db
      .select()
      .from(authThrottles)
      .where(eq(authThrottles.identifierHash, hashLoginIdentifier(email)))
      .limit(1);
    expect(record?.attemptCount).toBe(1);

    await clearLoginFailures(client.db, email);
    await expect(isLoginBlocked(client.db, email)).resolves.toBe(false);
    await expect(client.db.select().from(authThrottles)).resolves.toHaveLength(0);
  }, 20_000);
});
