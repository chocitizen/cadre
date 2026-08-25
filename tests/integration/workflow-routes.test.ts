import { eq } from "drizzle-orm";
import { NextRequest } from "next/server";
import { afterEach, describe, expect, it } from "vitest";

import { GET as getArtifact } from "../../src/app/api/artifacts/[artifactId]/route";
import { POST as createArtifact } from "../../src/app/api/artifacts/route";
import { GET as getConversation } from "../../src/app/api/conversations/[conversationId]/route";
import { POST as sendMessage } from "../../src/app/api/conversations/[conversationId]/messages/route";
import { GET as getReadyDock } from "../../src/app/api/ready-dock/route";
import {
  GET as listConversations,
  POST as createConversation
} from "../../src/app/api/workspaces/[workspaceId]/conversations/route";
import { hashPassword } from "../../src/server/auth/password";
import { createSession, type CreatedSession } from "../../src/server/auth/session";
import {
  closeDatabase,
  createDatabaseClient,
  runMigrations,
  users,
  workspaceMemberships,
  workspaces,
  type DatabaseClient
} from "../../src/server/db";

type DatabaseGlobal = typeof globalThis & {
  __cadreDatabaseClient?: Promise<DatabaseClient>;
};

const databaseGlobal = globalThis as DatabaseGlobal;
const originalEnvironment = {
  APP_URL: process.env.APP_URL,
  CADRE_AI_PROVIDER: process.env.CADRE_AI_PROVIDER,
  CADRE_ENABLE_TEST_PROVIDER: process.env.CADRE_ENABLE_TEST_PROVIDER
};

function authenticatedRequest(
  path: string,
  session: CreatedSession,
  options: { method?: "GET" | "POST"; body?: Record<string, unknown> } = {}
) {
  const method = options.method ?? "GET";
  return new NextRequest(`https://cadre.example${path}`, {
    method,
    headers: {
      ...(options.body ? { "content-type": "application/json" } : {}),
      cookie: `cadre_session=${session.token}; cadre_csrf=${session.csrfToken}`,
      ...(method === "POST"
        ? { origin: "https://cadre.example", "x-csrf-token": session.csrfToken }
        : {})
    },
    body: options.body ? JSON.stringify(options.body) : undefined
  });
}

async function useMigratedDatabase(): Promise<DatabaseClient> {
  const client = await createDatabaseClient({ inMemory: true });
  await runMigrations(client);
  databaseGlobal.__cadreDatabaseClient = Promise.resolve(client);
  return client;
}

afterEach(async () => {
  await closeDatabase();
  for (const [key, value] of Object.entries(originalEnvironment)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
});

describe("CADRE workflow routes", () => {
  it("persists a workspace chat and promotes its response through the Ready Dock", async () => {
    process.env.APP_URL = "https://cadre.example";
    process.env.CADRE_AI_PROVIDER = "test";
    process.env.CADRE_ENABLE_TEST_PROVIDER = "true";

    const client = await useMigratedDatabase();
    const [owner] = await client.db
      .insert(users)
      .values({
        email: "workflow-owner@example.com",
        displayName: "Workflow Owner",
        passwordHash: await hashPassword("a long workflow-only test passphrase"),
        role: "owner"
      })
      .returning();
    const [workspace] = await client.db
      .select()
      .from(workspaces)
      .where(eq(workspaces.slug, "vessel"))
      .limit(1);
    expect(owner).toBeDefined();
    expect(workspace).toBeDefined();

    await client.db.insert(workspaceMemberships).values({
      workspaceId: workspace!.id,
      userId: owner!.id,
      role: "owner"
    });
    const session = await createSession(client.db, owner!.id);

    const createResponse = await createConversation(
      authenticatedRequest(`/api/workspaces/${workspace!.id}/conversations`, session, {
        method: "POST",
        body: { title: "Governed workflow" }
      }),
      { params: Promise.resolve({ workspaceId: workspace!.id }) }
    );
    expect(createResponse.status).toBe(201);
    const { conversation } = await createResponse.json();

    const listResponse = await listConversations(
      authenticatedRequest(`/api/workspaces/${workspace!.id}/conversations`, session),
      { params: Promise.resolve({ workspaceId: workspace!.id }) }
    );
    expect(listResponse.status).toBe(200);
    await expect(listResponse.json()).resolves.toMatchObject({
      conversations: [{ id: conversation.id, workspaceId: workspace!.id }]
    });

    const messageResponse = await sendMessage(
      authenticatedRequest(`/api/conversations/${conversation.id}/messages`, session, {
        method: "POST",
        body: {
          content: "Return the governed test result.",
          clientRequestId: "4eae6ad8-9ea8-4b78-8d79-e0059439f226"
        }
      }),
      { params: Promise.resolve({ conversationId: conversation.id }) }
    );
    expect(messageResponse.status).toBe(201);
    const messagePayload = await messageResponse.json();
    expect(messagePayload).toMatchObject({
      assistantMessage: { content: "CADRE test response.", role: "assistant" },
      userMessage: { content: "Return the governed test result.", role: "user" }
    });

    const conversationResponse = await getConversation(
      authenticatedRequest(`/api/conversations/${conversation.id}`, session),
      { params: Promise.resolve({ conversationId: conversation.id }) }
    );
    expect(conversationResponse.status).toBe(200);
    await expect(conversationResponse.json()).resolves.toMatchObject({
      conversation: { id: conversation.id },
      messages: [{ role: "user" }, { role: "assistant" }]
    });

    const artifactResponse = await createArtifact(
      authenticatedRequest("/api/artifacts", session, {
        method: "POST",
        body: {
          conversationId: conversation.id,
          messageId: messagePayload.assistantMessage.id,
          title: "Governed workflow — CADRE response"
        }
      })
    );
    expect(artifactResponse.status).toBe(201);
    const artifactPayload = await artifactResponse.json();
    expect(artifactPayload).toMatchObject({
      artifact: {
        content: "CADRE test response.",
        currentVersion: 1,
        type: "markdown"
      },
      readyDock: {
        actionPath: `/app/artifacts/${artifactPayload.artifact.id}`
      }
    });

    const artifactGetResponse = await getArtifact(
      authenticatedRequest(`/api/artifacts/${artifactPayload.artifact.id}`, session),
      { params: Promise.resolve({ artifactId: artifactPayload.artifact.id }) }
    );
    expect(artifactGetResponse.status).toBe(200);
    await expect(artifactGetResponse.json()).resolves.toMatchObject({
      artifact: {
        checksum: expect.stringMatching(/^[0-9a-f]{64}$/),
        content: "CADRE test response."
      }
    });

    const dockResponse = await getReadyDock(
      authenticatedRequest("/api/ready-dock?limit=10", session)
    );
    expect(dockResponse.status).toBe(200);
    await expect(dockResponse.json()).resolves.toMatchObject({
      items: [
        {
          actionPath: `/app/artifacts/${artifactPayload.artifact.id}`,
          artifactId: artifactPayload.artifact.id,
          status: "ready",
          workspaceId: workspace!.id
        }
      ]
    });
  }, 40_000);

  it("does not allow a viewer to create a workspace conversation", async () => {
    process.env.APP_URL = "https://cadre.example";
    const client = await useMigratedDatabase();
    const [viewer] = await client.db
      .insert(users)
      .values({
        email: "workflow-viewer@example.com",
        displayName: "Workflow Viewer",
        passwordHash: await hashPassword("a long viewer-only test passphrase"),
        role: "member"
      })
      .returning();
    const [workspace] = await client.db
      .select()
      .from(workspaces)
      .where(eq(workspaces.slug, "vessel"))
      .limit(1);

    await client.db.insert(workspaceMemberships).values({
      workspaceId: workspace!.id,
      userId: viewer!.id,
      role: "viewer"
    });
    const session = await createSession(client.db, viewer!.id);
    const response = await createConversation(
      authenticatedRequest(`/api/workspaces/${workspace!.id}/conversations`, session, {
        method: "POST",
        body: { title: "Not authorized" }
      }),
      { params: Promise.resolve({ workspaceId: workspace!.id }) }
    );

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({
      error: { code: "not_found", message: "Workspace was not found." }
    });
  }, 30_000);
});
