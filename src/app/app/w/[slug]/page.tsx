import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { NewConversationForm } from "@/components/new-conversation-form";
import { requirePageSession } from "@/server/auth";
import { getDatabase } from "@/server/db";
import { getUserWorkspaceBySlug, listWorkspaceConversations } from "@/server/data";

export const metadata: Metadata = { title: "Workspace" };

export default async function WorkspacePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const db = await getDatabase();
  const { user } = await requirePageSession(db);
  const workspace = await getUserWorkspaceBySlug(db, user.id, slug);
  if (!workspace) notFound();

  const conversations = await listWorkspaceConversations(db, workspace.id);

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="section-label">Governed workspace</p>
          <h1>{workspace.name}</h1>
          <p>{workspace.description}</p>
        </div>
        <span className="status status-canonical">Operational container</span>
      </header>

      <section className="workspace-composer">
        <NewConversationForm workspaceId={workspace.id} />
      </section>

      <section className="surface-section">
        <div className="surface-heading">
          <h2>Conversation history</h2>
          <span className="metadata">{conversations.length} records</span>
        </div>
        {conversations.length === 0 ? (
          <div className="empty-state">
            <h3>No conversation history yet.</h3>
            <p>
              Begin with a clear objective. CADRE will retain the messages, provider metadata, and
              resulting artifacts inside this workspace boundary.
            </p>
          </div>
        ) : (
          <ul className="row-list">
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <Link className="row-link" href={`/app/c/${conversation.id}`}>
                  <span className="row-title">{conversation.title}</span>
                  <span className="row-secondary">
                    {conversation.provider ?? "No provider call"}
                  </span>
                  <span className="status status-ready">{conversation.status}</span>
                  <time className="metadata" dateTime={conversation.updatedAt}>
                    {new Date(conversation.updatedAt).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric"
                    })}
                  </time>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {workspace.slug === "vessel" && (
        <aside className="boundary-note">
          <strong>VESSEL boundary</strong>
          <p>
            This is the governed VESSEL workspace inside CADRE. The full customer-facing VESSEL
            application is intentionally outside Foundation v0.1.
          </p>
        </aside>
      )}
    </div>
  );
}
