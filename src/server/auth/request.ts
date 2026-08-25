import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";

import { getDatabase, type CadreDatabase } from "@/server/db";

import { assertMutationSecurity } from "./csrf";
import { requireAuthenticatedSession } from "./authorize";
import { getSessionCookieName, type AuthenticatedSession } from "./session";

function sessionTokenFromRequest(request: NextRequest): string {
  return request.cookies.get(getSessionCookieName())?.value ?? "";
}

export async function authenticateApiRequest(
  request: NextRequest,
  options: { mutation?: boolean; database?: CadreDatabase } = {}
): Promise<AuthenticatedSession> {
  const db = options.database ?? (await getDatabase());
  const authenticated = await requireAuthenticatedSession(db, sessionTokenFromRequest(request));

  if (options.mutation) {
    assertMutationSecurity(request, authenticated.session.csrfTokenHash, process.env.APP_URL);
  }

  return authenticated;
}

export async function getPageSession(
  database?: CadreDatabase
): Promise<AuthenticatedSession | null> {
  const db = database ?? (await getDatabase());
  const cookieStore = await cookies();
  const token = cookieStore.get(getSessionCookieName())?.value ?? "";

  try {
    return await requireAuthenticatedSession(db, token);
  } catch {
    return null;
  }
}

export async function requirePageSession(database?: CadreDatabase): Promise<AuthenticatedSession> {
  const authenticated = await getPageSession(database);
  if (!authenticated) redirect("/login");
  return authenticated;
}
