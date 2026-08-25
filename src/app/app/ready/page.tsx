import type { Metadata } from "next";
import Link from "next/link";

import type { ReadyDockItem } from "@/lib/types";
import { requirePageSession } from "@/server/auth";
import { listReadyDock } from "@/server/data";
import { getDatabase } from "@/server/db";

export const metadata: Metadata = { title: "Ready Dock" };

const categories = [
  ["ready", "Ready"],
  ["in_progress", "In progress"],
  ["needs_approval", "Needs approval"],
  ["scheduled", "Scheduled"],
  ["failed", "Failed"],
  ["archived", "Archived"]
] as const;

function DockRows({ items }: { items: ReadyDockItem[] }) {
  return (
    <ul className="row-list">
      {items.map((item) => (
        <li key={item.jobId}>
          <Link className="row-link" href={item.actionPath ?? "/app/ready"}>
            <span className="row-title">{item.title}</span>
            <span className="row-secondary">{item.workspaceName}</span>
            <span className={`status status-${item.status}`}>
              {item.status.replaceAll("_", " ")}
            </span>
            <time className="metadata" dateTime={item.completedAt ?? item.createdAt}>
              {new Date(item.completedAt ?? item.createdAt).toISOString().slice(0, 10)}
            </time>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default async function ReadyDockPage() {
  const db = await getDatabase();
  const { user } = await requirePageSession(db);
  const items = await listReadyDock(db, user.id);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="section-label">Durable delivery surface</p>
          <h1>Ready Dock</h1>
          <p>
            Open exact, persisted deliverables without retracing their originating conversation.
          </p>
        </div>
        <span className="metadata">{items.length} tracked jobs</span>
      </header>

      {items.length === 0 ? (
        <section className="empty-state surface-section">
          <h2>The dock is clear.</h2>
          <p>
            Save a CADRE response as Markdown to create the first durable artifact and delivery
            record.
          </p>
        </section>
      ) : (
        categories.map(([status, label]) => {
          const categoryItems = items.filter((item) => item.status === status);
          if (categoryItems.length === 0) return null;
          return (
            <section className="surface-section" key={status}>
              <div className="surface-heading">
                <h2>{label}</h2>
                <span className="metadata">{categoryItems.length}</span>
              </div>
              <DockRows items={categoryItems} />
            </section>
          );
        })
      )}
    </div>
  );
}
