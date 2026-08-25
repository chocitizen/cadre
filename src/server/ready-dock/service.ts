import { and, desc, eq } from "drizzle-orm";

import { getDatabase } from "../db/client";
import { readyDockItems } from "../db/schema";
import { openNotification } from "../notifications/service";

export const READY_DOCK_STATUSES = [
  "ready",
  "in_progress",
  "needs_approval",
  "scheduled",
  "failed",
  "archived"
] as const;

export type ReadyDockStatus = (typeof READY_DOCK_STATUSES)[number];
export type ReadyDockItem = typeof readyDockItems.$inferSelect;

export interface ListReadyDockOptions {
  readonly workspaceId?: string;
  readonly status?: ReadyDockStatus;
  readonly limit?: number;
}

export async function listReadyDockItems(
  requestedByUserId: string,
  options: ListReadyDockOptions = {}
): Promise<ReadyDockItem[]> {
  const db = await getDatabase();
  const filters = [eq(readyDockItems.requestedByUserId, requestedByUserId)];

  if (options.workspaceId) {
    filters.push(eq(readyDockItems.workspaceId, options.workspaceId));
  }

  if (options.status) {
    filters.push(eq(readyDockItems.dockStatus, options.status));
  }

  return db
    .select()
    .from(readyDockItems)
    .where(and(...filters))
    .orderBy(desc(readyDockItems.createdAt))
    .limit(Math.min(Math.max(options.limit ?? 50, 1), 100));
}

export async function getReadyDockItem(
  requestedByUserId: string,
  itemId: string
): Promise<ReadyDockItem | null> {
  const db = await getDatabase();
  const [item] = await db
    .select()
    .from(readyDockItems)
    .where(
      and(eq(readyDockItems.id, itemId), eq(readyDockItems.requestedByUserId, requestedByUserId))
    )
    .limit(1);

  return item ?? null;
}

export async function openReadyDockItem(
  requestedByUserId: string,
  itemId: string
): Promise<{ readonly item: ReadyDockItem; readonly actionPath: string }> {
  const item = await getReadyDockItem(requestedByUserId, itemId);

  if (!item?.actionPath) {
    throw new Error("The Ready Dock item has no available deliverable.");
  }

  if (item.notificationId) {
    await openNotification({
      notificationId: item.notificationId,
      userId: requestedByUserId
    });
  }

  return { item, actionPath: item.actionPath };
}
