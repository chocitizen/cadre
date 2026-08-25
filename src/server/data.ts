import { and, desc, eq, inArray } from "drizzle-orm";

import type {
  ArtifactSummary,
  ConversationSummary,
  MessageDto,
  ReadyDockItem,
  WorkspaceSummary
} from "@/lib/types";
import type { CadreDatabase } from "@/server/db";
import {
  artifactVersions,
  artifacts,
  auditEvents,
  conversations,
  messages,
  readyDockItems,
  workspaceMemberships,
  workspaces
} from "@/server/db";

function iso(value: Date): string {
  return value.toISOString();
}

export async function listUserWorkspaces(
  db: CadreDatabase,
  userId: string
): Promise<WorkspaceSummary[]> {
  const rows = await db
    .select({
      id: workspaces.id,
      slug: workspaces.slug,
      name: workspaces.name,
      description: workspaces.description,
      status: workspaces.status
    })
    .from(workspaceMemberships)
    .innerJoin(workspaces, eq(workspaces.id, workspaceMemberships.workspaceId))
    .where(and(eq(workspaceMemberships.userId, userId), eq(workspaces.status, "active")))
    .orderBy(workspaces.name);

  return rows;
}

export async function getUserWorkspaceBySlug(
  db: CadreDatabase,
  userId: string,
  slug: string
): Promise<WorkspaceSummary | null> {
  const [workspace] = await db
    .select({
      id: workspaces.id,
      slug: workspaces.slug,
      name: workspaces.name,
      description: workspaces.description,
      status: workspaces.status
    })
    .from(workspaceMemberships)
    .innerJoin(workspaces, eq(workspaces.id, workspaceMemberships.workspaceId))
    .where(
      and(
        eq(workspaceMemberships.userId, userId),
        eq(workspaces.slug, slug),
        eq(workspaces.status, "active")
      )
    )
    .limit(1);

  return workspace ?? null;
}

export async function listWorkspaceConversations(
  db: CadreDatabase,
  workspaceId: string,
  limit = 50
): Promise<ConversationSummary[]> {
  const rows = await db
    .select()
    .from(conversations)
    .where(and(eq(conversations.workspaceId, workspaceId), eq(conversations.status, "active")))
    .orderBy(desc(conversations.lastMessageAt), desc(conversations.createdAt))
    .limit(limit);

  return rows.map((conversation) => ({
    id: conversation.id,
    workspaceId: conversation.workspaceId,
    title: conversation.title,
    status: conversation.status,
    provider: conversation.provider,
    model: conversation.model,
    createdAt: iso(conversation.createdAt),
    updatedAt: iso(conversation.updatedAt)
  }));
}

export async function getAuthorizedConversation(
  db: CadreDatabase,
  userId: string,
  conversationId: string
): Promise<{
  conversation: ConversationSummary;
  workspace: WorkspaceSummary;
  messages: MessageDto[];
} | null> {
  const [row] = await db
    .select({ conversation: conversations, workspace: workspaces })
    .from(conversations)
    .innerJoin(workspaces, eq(workspaces.id, conversations.workspaceId))
    .innerJoin(
      workspaceMemberships,
      and(
        eq(workspaceMemberships.workspaceId, conversations.workspaceId),
        eq(workspaceMemberships.userId, userId)
      )
    )
    .where(eq(conversations.id, conversationId))
    .limit(1);

  if (!row) return null;

  const messageRows = await db
    .select()
    .from(messages)
    .where(eq(messages.conversationId, conversationId))
    .orderBy(messages.sequence);

  return {
    conversation: {
      id: row.conversation.id,
      workspaceId: row.conversation.workspaceId,
      title: row.conversation.title,
      status: row.conversation.status,
      provider: row.conversation.provider,
      model: row.conversation.model,
      createdAt: iso(row.conversation.createdAt),
      updatedAt: iso(row.conversation.updatedAt)
    },
    workspace: {
      id: row.workspace.id,
      slug: row.workspace.slug,
      name: row.workspace.name,
      description: row.workspace.description,
      status: row.workspace.status
    },
    messages: messageRows.map((message) => ({
      id: message.id,
      conversationId: message.conversationId,
      role: message.role as MessageDto["role"],
      content: message.contentText,
      provider: message.provider,
      model: message.model,
      createdAt: iso(message.createdAt)
    }))
  };
}

export async function getAuthorizedArtifact(
  db: CadreDatabase,
  userId: string,
  artifactId: string
): Promise<(ArtifactSummary & { workspace: WorkspaceSummary }) | null> {
  const [row] = await db
    .select({ artifact: artifacts, version: artifactVersions, workspace: workspaces })
    .from(artifacts)
    .innerJoin(
      artifactVersions,
      and(
        eq(artifactVersions.artifactId, artifacts.id),
        eq(artifactVersions.version, artifacts.currentVersion)
      )
    )
    .innerJoin(workspaces, eq(workspaces.id, artifacts.workspaceId))
    .innerJoin(
      workspaceMemberships,
      and(
        eq(workspaceMemberships.workspaceId, artifacts.workspaceId),
        eq(workspaceMemberships.userId, userId)
      )
    )
    .where(eq(artifacts.id, artifactId))
    .limit(1);

  if (!row) return null;

  return {
    id: row.artifact.id,
    workspaceId: row.artifact.workspaceId,
    conversationId: row.artifact.conversationId,
    jobId: row.artifact.sourceJobId,
    title: row.artifact.title,
    type: row.artifact.kind,
    currentVersion: row.artifact.currentVersion,
    approvalState: row.artifact.approvalState,
    checksum: row.version.checksumSha256,
    content: row.version.contentText ?? undefined,
    createdAt: iso(row.artifact.createdAt),
    updatedAt: iso(row.artifact.updatedAt),
    workspace: {
      id: row.workspace.id,
      slug: row.workspace.slug,
      name: row.workspace.name,
      description: row.workspace.description,
      status: row.workspace.status
    }
  };
}

export async function listReadyDock(
  db: CadreDatabase,
  userId: string,
  limit = 100
): Promise<ReadyDockItem[]> {
  const rows = await db
    .select({
      jobId: readyDockItems.id,
      title: readyDockItems.title,
      workspaceId: readyDockItems.workspaceId,
      workspaceName: workspaces.name,
      workspaceSlug: workspaces.slug,
      status: readyDockItems.dockStatus,
      createdAt: readyDockItems.createdAt,
      completedAt: readyDockItems.completedAt,
      conversationId: readyDockItems.conversationId,
      artifactId: readyDockItems.artifactId,
      artifactVersion: readyDockItems.artifactVersion,
      approvalState: readyDockItems.approvalState,
      actionPath: readyDockItems.actionPath
    })
    .from(readyDockItems)
    .innerJoin(workspaces, eq(workspaces.id, readyDockItems.workspaceId))
    .innerJoin(
      workspaceMemberships,
      and(
        eq(workspaceMemberships.workspaceId, readyDockItems.workspaceId),
        eq(workspaceMemberships.userId, userId)
      )
    )
    .where(eq(readyDockItems.requestedByUserId, userId))
    .orderBy(desc(readyDockItems.createdAt))
    .limit(limit);

  return rows.map((item) => ({
    ...item,
    createdAt: iso(item.createdAt),
    completedAt: item.completedAt ? iso(item.completedAt) : null
  }));
}

export async function listRecentAuditEvents(
  db: CadreDatabase,
  workspaceIds: string[],
  limit = 100
) {
  if (workspaceIds.length === 0) return [];

  const rows = await db
    .select()
    .from(auditEvents)
    .where(inArray(auditEvents.workspaceId, workspaceIds))
    .orderBy(desc(auditEvents.createdAt))
    .limit(limit);

  return rows.map((event) => ({
    id: event.id,
    eventType: event.eventType,
    targetType: event.targetType,
    outcome: event.outcome,
    workspaceId: event.workspaceId,
    createdAt: iso(event.createdAt),
    metadata: event.metadata
  }));
}
