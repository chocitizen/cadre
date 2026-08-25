import { eq } from "drizzle-orm";
import { afterEach, describe, expect, it } from "vitest";

import { AuthorizationError, requireWorkspaceAccess } from "../../src/server/auth/authorize";
import { hashPassword } from "../../src/server/auth/password";
import { createSession, findActiveSession } from "../../src/server/auth/session";
import {
  INITIAL_WORKSPACES,
  createDatabaseClient,
  runMigrations,
  seedWorkspaces,
  sessions,
  users,
  workspaceMemberships,
  workspaces,
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

describe("CADRE database foundation", () => {
  it("migrates once and seeds the exact canonical workspace set idempotently", async () => {
    const client = await migratedDatabase();

    await expect(runMigrations(client)).resolves.toEqual([]);
    await expect(seedWorkspaces(client.db)).resolves.toBe(0);
    const rows = await client.db.select({ slug: workspaces.slug }).from(workspaces);

    expect(rows.map((row) => row.slug).sort()).toEqual(
      INITIAL_WORKSPACES.map(({ slug }) => slug).sort()
    );
    expect(rows).toHaveLength(8);
  }, 20_000);

  it("stores only hashed session credentials and enforces workspace membership", async () => {
    const client = await migratedDatabase();
    const db = client.db;
    const [owner] = await db
      .insert(users)
      .values({
        email: "owner@example.com",
        displayName: "CADRE Owner",
        passwordHash: await hashPassword("a long owner-only test passphrase"),
        role: "owner"
      })
      .returning();
    const [vessel] = await db
      .select()
      .from(workspaces)
      .where(eq(workspaces.slug, "vessel"))
      .limit(1);
    expect(owner).toBeDefined();
    expect(vessel).toBeDefined();

    await db
      .insert(workspaceMemberships)
      .values({ workspaceId: vessel!.id, userId: owner!.id, role: "owner" });
    const created = await createSession(db, owner!.id);
    const stored = await db
      .select()
      .from(sessions)
      .where(eq(sessions.id, created.session.id))
      .limit(1);

    expect(stored[0]?.tokenHash).not.toBe(created.token);
    expect(stored[0]?.csrfTokenHash).not.toBe(created.csrfToken);
    await expect(findActiveSession(db, created.token)).resolves.toMatchObject({
      user: { id: owner!.id }
    });
    await expect(requireWorkspaceAccess(db, owner!.id, "vessel", ["owner"])).resolves.toMatchObject(
      {
        workspace: { id: vessel!.id },
        membershipRole: "owner"
      }
    );
    await expect(
      requireWorkspaceAccess(db, owner!.id, "incubator", ["owner"])
    ).rejects.toBeInstanceOf(AuthorizationError);
  }, 20_000);

  it("exposes the Ready Dock view and records migration provenance", async () => {
    const client = await migratedDatabase();
    const result = await client.query<{ count: number } & Record<string, unknown>>(
      "SELECT count(*)::int AS count FROM ready_dock_items"
    );
    expect(result[0]?.count).toBe(0);

    const migrationRows = await client.query<{ id: string } & Record<string, unknown>>(
      "SELECT id FROM cadre_schema_migrations"
    );
    expect(migrationRows).toEqual([
      { id: "0001_cadre_foundation" },
      { id: "0002_ready_dock_action_path" }
    ]);
  }, 20_000);
});
