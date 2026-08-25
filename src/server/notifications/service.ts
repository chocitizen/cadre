import { and, desc, eq } from "drizzle-orm";

import { getDatabase } from "../db/client";
import { NOTIFICATION_STATUSES, notifications, type Notification } from "../db/schema";

export type NotificationStatus = (typeof NOTIFICATION_STATUSES)[number];

export interface CreateNotificationInput {
  readonly userId: string;
  readonly workspaceId: string;
  readonly jobId?: string | null;
  readonly artifactId?: string | null;
  readonly type: string;
  readonly title: string;
  readonly body?: string | null;
  readonly actionPath: string;
}

export interface NotificationIdentity {
  readonly notificationId: string;
  readonly userId: string;
}

function validateActionPath(actionPath: string): string {
  const normalizedPath = actionPath.trim();

  if (
    !normalizedPath.startsWith("/") ||
    normalizedPath.startsWith("//") ||
    /[\r\n\0]/.test(normalizedPath)
  ) {
    throw new Error("A safe application-relative notification path is required.");
  }

  return normalizedPath;
}

export async function createNotification(input: CreateNotificationInput): Promise<Notification> {
  const type = input.type.trim();
  const title = input.title.trim();

  if (!type || !title) {
    throw new Error("Notification type and title are required.");
  }

  const db = await getDatabase();
  const [notification] = await db
    .insert(notifications)
    .values({
      userId: input.userId,
      workspaceId: input.workspaceId,
      jobId: input.jobId ?? null,
      artifactId: input.artifactId ?? null,
      type,
      title,
      body: input.body?.trim() || null,
      status: "unread",
      actionPath: validateActionPath(input.actionPath)
    })
    .returning();

  if (!notification) {
    throw new Error("The notification was not persisted.");
  }

  return notification;
}

export async function listNotifications(
  userId: string,
  options: {
    readonly workspaceId?: string;
    readonly status?: NotificationStatus;
    readonly limit?: number;
  } = {}
): Promise<Notification[]> {
  const db = await getDatabase();
  const filters = [eq(notifications.userId, userId)];

  if (options.workspaceId) {
    filters.push(eq(notifications.workspaceId, options.workspaceId));
  }

  if (options.status) {
    filters.push(eq(notifications.status, options.status));
  }

  return db
    .select()
    .from(notifications)
    .where(and(...filters))
    .orderBy(desc(notifications.createdAt))
    .limit(Math.min(Math.max(options.limit ?? 50, 1), 100));
}

async function updateNotificationStatus(
  identity: NotificationIdentity,
  status: NotificationStatus,
  timestamps: { readonly readAt?: Date; readonly openedAt?: Date } = {}
): Promise<Notification> {
  const db = await getDatabase();
  const [notification] = await db
    .update(notifications)
    .set({
      status,
      ...timestamps,
      updatedAt: new Date()
    })
    .where(
      and(eq(notifications.id, identity.notificationId), eq(notifications.userId, identity.userId))
    )
    .returning();

  if (!notification) {
    throw new Error("The notification is unavailable.");
  }

  return notification;
}

export function markNotificationRead(identity: NotificationIdentity): Promise<Notification> {
  return updateNotificationStatus(identity, "read", { readAt: new Date() });
}

export function openNotification(identity: NotificationIdentity): Promise<Notification> {
  const now = new Date();
  return updateNotificationStatus(identity, "read", {
    readAt: now,
    openedAt: now
  });
}

export function archiveNotification(identity: NotificationIdentity): Promise<Notification> {
  return updateNotificationStatus(identity, "archived");
}
