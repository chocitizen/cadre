import path from "node:path";
import { rm } from "node:fs/promises";

import { loadEnvConfig } from "@next/env";

import { hashPassword } from "../src/server/auth/password";
import {
  auditEvents,
  createDatabaseClient,
  runMigrations,
  seedWorkspaces,
  users,
  workspaceMemberships,
  workspaces
} from "../src/server/db";

loadEnvConfig(process.cwd(), true);

export const E2E_OWNER_EMAIL = "owner@cadre.test";
export const E2E_OWNER_PASSWORD = "CADRE local end-to-end passphrase!";

async function main() {
  const configuredPath = process.env.CADRE_DB_PATH;
  if (configuredPath !== "./data/e2e" || process.env.CADRE_ENABLE_TEST_PROVIDER !== "true") {
    throw new Error(
      "The E2E database reset requires the exact local test path and test provider gate."
    );
  }

  const databasePath = path.join(process.cwd(), "data", "e2e");
  await rm(databasePath, { recursive: true, force: true });

  const client = await createDatabaseClient({ pgliteDataDir: databasePath });

  try {
    await runMigrations(client);
    await seedWorkspaces(client.db);

    const [owner] = await client.db
      .insert(users)
      .values({
        email: E2E_OWNER_EMAIL,
        displayName: "CADRE Test Owner",
        passwordHash: await hashPassword(E2E_OWNER_PASSWORD),
        role: "owner",
        status: "active"
      })
      .returning();

    if (!owner) throw new Error("The E2E owner could not be prepared.");

    const workspaceRows = await client.db.select({ id: workspaces.id }).from(workspaces);
    await client.db.insert(workspaceMemberships).values(
      workspaceRows.map((workspace) => ({
        workspaceId: workspace.id,
        userId: owner.id,
        role: "owner" as const
      }))
    );
    await client.db.insert(auditEvents).values({
      actorUserId: owner.id,
      eventType: "owner.bootstrap",
      targetType: "user",
      targetId: owner.id,
      metadata: { source: "e2e_fixture" }
    });

    console.log("Isolated CADRE E2E database prepared.");
  } finally {
    await client.close();
  }
}

main().catch((cause: unknown) => {
  console.error(cause instanceof Error ? cause.message : "The E2E database could not be prepared.");
  process.exitCode = 1;
});
