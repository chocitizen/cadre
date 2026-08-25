import { loadEnvConfig } from "@next/env";

import { closeDatabase, runMigrations } from "../src/server/db";

loadEnvConfig(process.cwd(), process.env.NODE_ENV !== "production");

async function main(): Promise<void> {
  try {
    const applied = await runMigrations();
    console.log(
      applied.length === 0
        ? "Database schema is current."
        : `Applied ${applied.length} database migration(s).`
    );
  } catch {
    console.error("Database migration failed. No credential values were logged.");
    process.exitCode = 1;
  } finally {
    await closeDatabase();
  }
}

void main();
