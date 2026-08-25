import Link from "next/link";

import { requirePageSession } from "@/server/auth";
import { getDatabase } from "@/server/db";
import { listReadyDock, listUserWorkspaces } from "@/server/data";

function relativeTime(value: string): string {
  const elapsed = Date.now() - new Date(value).getTime();
  const minutes = Math.max(0, Math.floor(elapsed / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default async function CommandOverviewPage() {
  const db = await getDatabase();
  const { user } = await requirePageSession(db);
  const [workspaces, readyDock] = await Promise.all([
    listUserWorkspaces(db, user.id),
    listReadyDock(db, user.id, 6)
  ]);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="section-label">Command overview</p>
          <h1>Good to have you back, {user.displayName.split(" ")[0]}.</h1>
          <p>Move through governed workspaces, active execution, and exact deliverables.</p>
        </div>
        <div className="page-actions">
          <Link className="button button-primary" href="/app/w/vessel">
            Open VESSEL workspace
          </Link>
        </div>
      </header>

      <section className="command-posture" aria-label="System posture">
        <div>
          <span className="status status-ready">Local foundation active</span>
          <p>Private application state is stored locally. Public deployment remains gated.</p>
        </div>
        <div>
          <span className="status status-canonical">Doctrine inherited</span>
          <p>Obsidian remains authoritative for doctrine and canonical knowledge.</p>
        </div>
        <div>
          <span className="status status-canonical">AI gateway selected</span>
          <p>Live provider readiness is validated separately; calls remain server-side.</p>
        </div>
      </section>

      <section className="surface-section">
        <div className="surface-heading">
          <h2>Ready Dock</h2>
          <Link href="/app/ready">View all</Link>
        </div>
        {readyDock.length === 0 ? (
          <div className="empty-state">
            <h3>No deliverables are waiting.</h3>
            <p>
              Save an assistant response as Markdown and CADRE will persist it here with its job,
              version, and provenance.
            </p>
          </div>
        ) : (
          <ul className="row-list">
            {readyDock.map((item) => (
              <li key={item.jobId}>
                <Link className="row-link" href={item.actionPath ?? "/app/ready"}>
                  <span className="row-title">{item.title}</span>
                  <span className="row-secondary">{item.workspaceName}</span>
                  <span className={`status status-${item.status}`}>
                    {item.status.replaceAll("_", " ")}
                  </span>
                  <span className="metadata">
                    {relativeTime(item.completedAt ?? item.createdAt)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="surface-section">
        <div className="surface-heading">
          <h2>Governed workspaces</h2>
          <span className="metadata">{workspaces.length} active</span>
        </div>
        <div className="workspace-index">
          {workspaces.map((workspace) => (
            <Link className="workspace-entry" href={`/app/w/${workspace.slug}`} key={workspace.id}>
              <span>
                <strong>{workspace.name}</strong>
                <small>{workspace.description}</small>
              </span>
              <span aria-hidden="true">↗</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
