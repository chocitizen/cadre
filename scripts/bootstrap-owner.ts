import { stdin as input, stdout as output } from "node:process";
import { createInterface } from "node:readline/promises";

import { loadEnvConfig } from "@next/env";

import { normalizeEmail } from "../src/server/auth/authorize";
import { hashPassword } from "../src/server/auth/password";
import { closeDatabase, getDatabaseClient, runMigrations, seedWorkspaces } from "../src/server/db";

loadEnvConfig(process.cwd(), process.env.NODE_ENV !== "production");

function readFlag(flag: string): string | undefined {
  const index = process.argv.indexOf(flag);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

async function readVisible(prompt: string): Promise<string> {
  const readline = createInterface({ input, output });
  try {
    return (await readline.question(prompt)).trim();
  } finally {
    readline.close();
  }
}

function readHidden(prompt: string): Promise<string> {
  if (!input.isTTY || typeof input.setRawMode !== "function") {
    throw new Error("Owner bootstrap requires an interactive terminal.");
  }

  return new Promise((resolve, reject) => {
    let value = "";
    output.write(prompt);
    input.setEncoding("utf8");
    input.setRawMode(true);
    input.resume();

    const finish = (error?: Error) => {
      input.off("data", onData);
      input.setRawMode(false);
      input.pause();
      output.write("\n");
      if (error) reject(error);
      else resolve(value);
    };

    const onData = (chunk: string) => {
      for (const character of chunk) {
        if (character === "\u0003") {
          finish(new Error("Owner bootstrap cancelled."));
          return;
        }
        if (character === "\r" || character === "\n") {
          finish();
          return;
        }
        if (character === "\u007f" || character === "\b") {
          if (value.length > 0) {
            value = value.slice(0, -1);
            output.write("\b \b");
          }
          continue;
        }
        if (character >= " ") {
          value += character;
          output.write("*");
        }
      }
    };

    input.on("data", onData);
  });
}

async function main(): Promise<void> {
  if (process.argv.includes("--password")) {
    console.error(
      "Do not pass passwords as command-line arguments. The password is requested securely."
    );
    process.exitCode = 1;
    return;
  }

  try {
    await runMigrations();
    await seedWorkspaces();

    const rawEmail = readFlag("--email") ?? (await readVisible("Owner email: "));
    const displayName = readFlag("--name") ?? (await readVisible("Owner display name: "));
    const email = normalizeEmail(rawEmail);
    if (!/^\S+@\S+\.\S+$/.test(email) || !displayName) {
      throw new Error("A valid email and display name are required.");
    }

    const password = await readHidden("Owner password: ");
    const confirmation = await readHidden("Confirm owner password: ");
    if (password !== confirmation) {
      throw new Error("Passwords did not match.");
    }
    const passwordHash = await hashPassword(password);
    const client = await getDatabaseClient();
    const inserted = await client.query<{ actor_user_id: string } & Record<string, unknown>>(
      `
        WITH inserted_user AS (
          INSERT INTO users (email, display_name, password_hash, role, status)
          SELECT $1, $2, $3, 'owner', 'active'
          WHERE NOT EXISTS (SELECT 1 FROM users WHERE role = 'owner')
          RETURNING id
        ), inserted_memberships AS (
          INSERT INTO workspace_memberships (workspace_id, user_id, role)
          SELECT workspace.id, inserted_user.id, 'owner'
          FROM workspaces workspace
          CROSS JOIN inserted_user
          ON CONFLICT (workspace_id, user_id) DO NOTHING
          RETURNING workspace_id
        )
        INSERT INTO audit_events (actor_user_id, event_type, target_type, target_id, outcome, metadata)
        SELECT id, 'owner.bootstrap', 'user', id, 'success', '{"source":"operator_cli"}'::jsonb
        FROM inserted_user
        RETURNING actor_user_id
      `,
      [email, displayName, passwordHash]
    );

    if (inserted.length !== 1) {
      throw new Error(
        "An owner already exists; public or duplicate owner creation is not allowed."
      );
    }

    console.log("Owner account created and granted access to all canonical workspaces.");
  } catch (error) {
    const safeMessage = error instanceof Error ? error.message : "Owner bootstrap failed.";
    console.error(safeMessage);
    process.exitCode = 1;
  } finally {
    await closeDatabase();
  }
}

void main();
