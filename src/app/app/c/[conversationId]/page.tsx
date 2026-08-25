import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ChatPanel } from "@/components/chat-panel";
import { requirePageSession } from "@/server/auth";
import { getAuthorizedConversation } from "@/server/data";
import { getDatabase } from "@/server/db";

export const metadata: Metadata = { title: "Conversation" };

export default async function ConversationPage({
  params
}: {
  params: Promise<{ conversationId: string }>;
}) {
  const { conversationId } = await params;
  const db = await getDatabase();
  const { user } = await requirePageSession(db);
  const result = await getAuthorizedConversation(db, user.id, conversationId);
  if (!result) notFound();

  return (
    <div className="page conversation-page">
      <header className="page-header conversation-header">
        <div>
          <Link className="section-label breadcrumb" href={`/app/w/${result.workspace.slug}`}>
            {result.workspace.name} / Conversation
          </Link>
          <h1>{result.conversation.title}</h1>
          <p>Persistent, workspace-bound dialogue with explicit artifact promotion.</p>
        </div>
        <span className="status status-ready">{result.conversation.status}</span>
      </header>
      <ChatPanel conversation={result.conversation} initialMessages={result.messages} />
    </div>
  );
}
