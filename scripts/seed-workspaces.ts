import { loadEnvConfig } from "@next/env";

import { closeDatabase, runMigrations, seedWorkspaces } from "../src/server/db";

loadEnvConfig(process.cwd(), process.env.NODE_ENV !== "production");

async function main(): Promise<void> {
  try {
    await runMigrations();
    const insertedCount = await seedWorkspaces();
    console.log(
      insertedCount === 0
        ? "Canonical workspaces are already seeded."
        : `Seeded ${insertedCount} canonical workspace(s).`
    );
  } catch {
    console.error("Workspace seeding failed. No credential values were logged.");
    process.exitCode = 1;
  } finally {
    await closeDatabase();
  }
}

void main();
