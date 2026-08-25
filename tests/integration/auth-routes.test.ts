import { afterEach, describe, expect, it } from "vitest";
import { NextRequest } from "next/server";

import { POST as login } from "../../src/app/api/auth/login/route";
import { POST as logout } from "../../src/app/api/auth/logout/route";
import { GET as getSession } from "../../src/app/api/auth/session/route";
import { GET as live } from "../../src/app/api/health/live/route";
import { GET as ready } from "../../src/app/api/health/ready/route";
import { hashPassword } from "../../src/server/auth/password";
import {
  closeDatabase,
  createDatabaseClient,
  runMigrations,
  users,
  type DatabaseClient
} from "../../src/server/db";

type DatabaseGlobal = typeof globalThis & {
  __cadreDatabaseClient?: Promise<DatabaseClient>;
};

const databaseGlobal = globalThis as DatabaseGlobal;
const originalAppUrl = process.env.APP_URL;

async function useMigratedDatabase(): Promise<DatabaseClient> {
  const client = await createDatabaseClient({ inMemory: true });
  await runMigrations(client);
  databaseGlobal.__cadreDatabaseClient = Promise.resolve(client);
  return client;
}

afterEach(async () => {
  await closeDatabase();
  if (originalAppUrl === undefined) delete process.env.APP_URL;
  else process.env.APP_URL = originalAppUrl;
});

describe("health routes", () => {
  it("distinguishes process liveness from migrated database readiness", async () => {
    await useMigratedDatabase();

    const liveResponse = live();
    const readyResponse = await ready();

    expect(liveResponse.status).toBe(200);
    await expect(liveResponse.json()).resolves.toMatchObject({ status: "live" });
    expect(readyResponse.status).toBe(200);
    await expect(readyResponse.json()).resolves.toMatchObject({
      checks: { database: "ready" },
      status: "ready"
    });
  }, 20_000);
});

describe("authentication routes", () => {
  it("rejects a login that lacks an exact request origin", async () => {
    process.env.APP_URL = "https://cadre.example";
    const response = await login(
      new NextRequest("https://cadre.example/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: "owner@example.com",
          password: "a long owner-only test passphrase"
        })
      })
    );

    expect(response.status).toBe(403);
    await expect(response.json()).resolves.toMatchObject({
      error: { code: "origin_rejected" }
    });
  });

  it("returns a generic failure for an unknown account", async () => {
    process.env.APP_URL = "https://cadre.example";
    await useMigratedDatabase();
    const response = await login(
      new NextRequest("https://cadre.example/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json", origin: "https://cadre.example" },
        body: JSON.stringify({
          email: "unknown@example.com",
          password: "a long unknown test passphrase"
        })
      })
    );

    expect(response.status).toBe(401);
    const payload = await response.json();
    expect(payload).toEqual({
      error: {
        code: "authentication_failed",
        message: "Sign-in could not be completed."
      }
    });
    expect(JSON.stringify(payload)).not.toContain("unknown@example.com");
  }, 20_000);

  it("creates, resolves, and revokes a protected session without returning credentials", async () => {
    process.env.APP_URL = "https://cadre.example";
    const client = await useMigratedDatabase();
    await client.db.insert(users).values({
      email: "owner@example.com",
      displayName: "CADRE Owner",
      passwordHash: await hashPassword("a long owner-only test passphrase"),
      role: "owner"
    });

    const loginResponse = await login(
      new NextRequest("https://cadre.example/api/auth/login", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          origin: "https://cadre.example",
          "user-agent": "CADRE test client"
        },
        body: JSON.stringify({
          email: "owner@example.com",
          password: "a long owner-only test passphrase"
        })
      })
    );
    expect(loginResponse.status).toBe(200);
    await expect(loginResponse.clone().json()).resolves.toEqual({ authenticated: true });

    const sessionCookie = loginResponse.cookies.get("cadre_session")?.value;
    const csrfCookie = loginResponse.cookies.get("cadre_csrf")?.value;
    expect(sessionCookie).toBeTruthy();
    expect(csrfCookie).toBeTruthy();
    expect(loginResponse.headers.get("set-cookie")).toContain("HttpOnly");

    const cookieHeader = `cadre_session=${sessionCookie}; cadre_csrf=${csrfCookie}`;
    const sessionResponse = await getSession(
      new NextRequest("https://cadre.example/api/auth/session", {
        headers: { cookie: cookieHeader }
      })
    );
    expect(sessionResponse.status).toBe(200);
    const sessionPayload = await sessionResponse.json();
    expect(sessionPayload).toMatchObject({
      authenticated: true,
      user: { email: "owner@example.com", role: "owner" }
    });
    expect(JSON.stringify(sessionPayload)).not.toContain("passphrase");
    expect(JSON.stringify(sessionPayload)).not.toContain(sessionCookie);
    expect(JSON.stringify(sessionPayload)).not.toContain(csrfCookie);

    const logoutResponse = await logout(
      new NextRequest("https://cadre.example/api/auth/logout", {
        method: "POST",
        headers: {
          cookie: cookieHeader,
          origin: "https://cadre.example",
          "x-csrf-token": csrfCookie!
        }
      })
    );
    expect(logoutResponse.status).toBe(200);
    await expect(logoutResponse.json()).resolves.toEqual({ authenticated: false });

    const revokedResponse = await getSession(
      new NextRequest("https://cadre.example/api/auth/session", {
        headers: { cookie: cookieHeader }
      })
    );
    expect(revokedResponse.status).toBe(401);
  }, 30_000);
});
