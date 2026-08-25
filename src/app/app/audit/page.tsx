import type { Metadata } from "next";

import { requirePageSession, requireUserRole } from "@/server/auth";
import { listRecentAuditEvents, listUserWorkspaces } from "@/server/data";
import { getDatabase } from "@/server/db";

export const metadata: Metadata = { title: "Audit trail" };

export default async function AuditPage() {
  const db = await getDatabase();
  const { user } = await requirePageSession(db);
  requireUserRole(user, ["owner", "admin"]);
  const workspaces = await listUserWorkspaces(db, user.id);
  const events = await listRecentAuditEvents(
    db,
    workspaces.map((workspace) => workspace.id)
  );
  const workspaceNames = new Map(workspaces.map((workspace) => [workspace.id, workspace.name]));

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="section-label">Material event record</p>
          <h1>Audit trail</h1>
          <p>
            Security, job-state, and artifact events retained without prompts, credentials, or
            content.
          </p>
        </div>
        <span className="status status-canonical">Owner visibility</span>
      </header>

      {events.length === 0 ? (
        <section className="empty-state surface-section">
          <h2>No material events recorded yet.</h2>
          <p>Authenticated work and durable artifact actions will appear here.</p>
        </section>
      ) : (
        <ol className="audit-list">
          {events.map((event) => (
            <li className="audit-event" key={event.id}>
              <div>
                <strong>{event.eventType.replaceAll(".", " · ")}</strong>
                <span
                  className={`status status-${event.outcome === "success" ? "ready" : "failed"}`}
                >
                  {event.outcome}
                </span>
              </div>
              <div className="audit-context">
                <span>
                  {event.workspaceId
                    ? (workspaceNames.get(event.workspaceId) ?? "Workspace")
                    : "Platform"}
                </span>
                <time className="metadata" dateTime={event.createdAt}>
                  {new Date(event.createdAt).toISOString().replace("T", " ").slice(0, 19)} UTC
                </time>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
