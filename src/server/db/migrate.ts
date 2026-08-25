import { createHash } from "node:crypto";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

import { getDatabaseClient, type DatabaseClient } from "./client";

export interface AppliedMigration extends Record<string, unknown> {
  id: string;
  checksum: string;
}

function quoteLiteral(value: string): string {
  return `'${value.replaceAll("'", "''")}'`;
}

export async function runMigrations(
  client?: DatabaseClient,
  migrationsDirectory = path.join(process.cwd(), "db", "migrations")
): Promise<string[]> {
  const activeClient = client ?? (await getDatabaseClient());
  await activeClient.execute(`
    CREATE TABLE IF NOT EXISTS cadre_schema_migrations (
      id text PRIMARY KEY,
      checksum text NOT NULL,
      applied_at timestamptz NOT NULL DEFAULT now()
    )
  `);

  const applied = await activeClient.query<AppliedMigration>(
    "SELECT id, checksum FROM cadre_schema_migrations ORDER BY id"
  );
  const appliedById = new Map(applied.map((migration) => [migration.id, migration.checksum]));
  const migrationFiles = (await readdir(migrationsDirectory))
    .filter((fileName) => /^\d+_[a-z0-9_-]+\.sql$/i.test(fileName))
    .sort();
  const newlyApplied: string[] = [];

  for (const fileName of migrationFiles) {
    const migrationId = fileName.slice(0, -4);
    const migrationSql = await readFile(path.join(migrationsDirectory, fileName), "utf8");
    const checksum = createHash("sha256").update(migrationSql).digest("hex");
    const priorChecksum = appliedById.get(migrationId);

    if (priorChecksum) {
      if (priorChecksum !== checksum) {
        throw new Error(
          `Applied migration ${migrationId} no longer matches its recorded checksum.`
        );
      }
      continue;
    }

    await activeClient.execute(`
      BEGIN;
      ${migrationSql}
      INSERT INTO cadre_schema_migrations (id, checksum)
      VALUES (${quoteLiteral(migrationId)}, ${quoteLiteral(checksum)});
      COMMIT;
    `);
    newlyApplied.push(migrationId);
  }

  return newlyApplied;
}
