import { and, eq } from "drizzle-orm";

import type { CadreDatabase } from "../db/client";
import {
  users,
  workspaceMemberships,
  workspaces,
  type User,
  type UserRole,
  type Workspace,
  type WorkspaceRole
} from "../db/schema";

import { findActiveSession, type AuthenticatedSession } from "./session";

export class AuthorizationError extends Error {
  readonly code: "UNAUTHENTICATED" | "FORBIDDEN" | "NOT_FOUND";
  readonly status: 401 | 403 | 404;

  constructor(code: "UNAUTHENTICATED" | "FORBIDDEN" | "NOT_FOUND", message: string) {
    super(message);
    this.name = "AuthorizationError";
    this.code = code;
    this.status = code === "UNAUTHENTICATED" ? 401 : code === "FORBIDDEN" ? 403 : 404;
  }
}

export interface AuthorizedWorkspace {
  workspace: Workspace;
  membershipRole: WorkspaceRole;
}

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export async function requireAuthenticatedSession(
  db: CadreDatabase,
  token: string
): Promise<AuthenticatedSession> {
  const authenticated = await findActiveSession(db, token);
  if (!authenticated) {
    throw new AuthorizationError("UNAUTHENTICATED", "Authentication is required.");
  }
  return authenticated;
}

export function requireUserRole(
  user: Pick<User, "role" | "status">,
  allowedRoles: readonly UserRole[]
): void {
  if (user.status !== "active" || !allowedRoles.includes(user.role)) {
    throw new AuthorizationError("FORBIDDEN", "This action is not authorized.");
  }
}

export async function requireWorkspaceAccess(
  db: CadreDatabase,
  userId: string,
  workspaceIdOrSlug: string,
  allowedRoles: readonly WorkspaceRole[] = ["owner", "admin", "member", "viewer"]
): Promise<AuthorizedWorkspace> {
  const workspaceSelector =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      workspaceIdOrSlug
    )
      ? eq(workspaces.id, workspaceIdOrSlug)
      : eq(workspaces.slug, workspaceIdOrSlug);
  const [result] = await db
    .select({ workspace: workspaces, membershipRole: workspaceMemberships.role })
    .from(workspaceMemberships)
    .innerJoin(workspaces, eq(workspaces.id, workspaceMemberships.workspaceId))
    .innerJoin(users, eq(users.id, workspaceMemberships.userId))
    .where(
      and(
        eq(workspaceMemberships.userId, userId),
        workspaceSelector,
        eq(workspaces.status, "active"),
        eq(users.status, "active")
      )
    )
    .limit(1);

  if (!result || !allowedRoles.includes(result.membershipRole)) {
    throw new AuthorizationError("NOT_FOUND", "Workspace was not found.");
  }

  return result;
}
