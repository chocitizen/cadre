import { mkdir } from "node:fs/promises";
import path from "node:path";

import { PGlite } from "@electric-sql/pglite";
import { drizzle as drizzlePglite, type PgliteDatabase } from "drizzle-orm/pglite";
import { drizzle as drizzlePostgres, type PostgresJsDatabase } from "drizzle-orm/postgres-js";
import postgres, { type Sql } from "postgres";

import * as schema from "./schema";

export type CadreDatabase = PostgresJsDatabase<typeof schema> | PgliteDatabase<typeof schema>;
export type DatabaseKind = "postgres" | "pglite";

export interface DatabaseClient {
  readonly kind: DatabaseKind;
  readonly db: CadreDatabase;
  execute(statement: string): Promise<void>;
  query<T extends Record<string, unknown>>(
    statement: string,
    parameters?: readonly unknown[]
  ): Promise<T[]>;
  close(): Promise<void>;
}

export interface CreateDatabaseClientOptions {
  databaseUrl?: string;
  pgliteDataDir?: string;
  inMemory?: boolean;
}

async function createPostgresClient(databaseUrl: string): Promise<DatabaseClient> {
  const parsed = new URL(databaseUrl);
  if (parsed.protocol !== "postgres:" && parsed.protocol !== "postgresql:") {
    throw new Error("DATABASE_URL must use the postgres or postgresql protocol.");
  }

  const sqlClient: Sql = postgres(databaseUrl, {
    max: 10,
    idle_timeout: 20,
    connect_timeout: 10,
    connection: { application_name: "cadre" }
  });
  const db = drizzlePostgres(sqlClient, { schema });

  await sqlClient`select 1`;

  return {
    kind: "postgres",
    db,
    async execute(statement) {
      await sqlClient.unsafe(statement);
    },
    async query<T extends Record<string, unknown>>(
      statement: string,
      parameters: readonly unknown[] = []
    ) {
      const rows = await sqlClient.unsafe(statement, parameters as never[]);
      return Array.from(rows) as unknown as T[];
    },
    async close() {
      await sqlClient.end({ timeout: 5 });
    }
  };
}

async function createPgliteClient(options: CreateDatabaseClientOptions): Promise<DatabaseClient> {
  const dataDir = options.inMemory
    ? undefined
    : (options.pgliteDataDir ??
      process.env.CADRE_DB_PATH ??
      process.env.PGLITE_DATA_DIR ??
      "data/pglite");
  if (dataDir) {
    await mkdir(path.dirname(path.resolve(dataDir)), { recursive: true });
  }
  const pglite = dataDir ? new PGlite(path.resolve(dataDir)) : new PGlite();
  await pglite.waitReady;
  const db = drizzlePglite(pglite, { schema });

  return {
    kind: "pglite",
    db,
    async execute(statement) {
      await pglite.exec(statement);
    },
    async query<T extends Record<string, unknown>>(
      statement: string,
      parameters: readonly unknown[] = []
    ) {
      const result = await pglite.query<T>(statement, [...parameters]);
      return result.rows;
    },
    async close() {
      await pglite.close();
    }
  };
}

export async function createDatabaseClient(
  options: CreateDatabaseClientOptions = {}
): Promise<DatabaseClient> {
  const databaseUrl = options.databaseUrl ?? process.env.DATABASE_URL;
  return databaseUrl ? createPostgresClient(databaseUrl) : createPgliteClient(options);
}

type DatabaseGlobal = typeof globalThis & {
  __cadreDatabaseClient?: Promise<DatabaseClient>;
};

const databaseGlobal = globalThis as DatabaseGlobal;

export function getDatabaseClient(): Promise<DatabaseClient> {
  databaseGlobal.__cadreDatabaseClient ??= createDatabaseClient();
  return databaseGlobal.__cadreDatabaseClient;
}

export async function getDatabase(): Promise<CadreDatabase> {
  return (await getDatabaseClient()).db;
}

export async function closeDatabase(): Promise<void> {
  const pendingClient = databaseGlobal.__cadreDatabaseClient;
  delete databaseGlobal.__cadreDatabaseClient;
  if (pendingClient) {
    await (await pendingClient).close();
  }
}
