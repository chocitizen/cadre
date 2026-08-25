"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

import { apiRequest } from "@/lib/client-api";
import type { ArtifactSummary, ConversationSummary, MessageDto } from "@/lib/types";

function messageTime(value: string): string {
  return `${new Date(value).toISOString().slice(11, 16)} UTC`;
}

export function ChatPanel({
  conversation,
  initialMessages
}: {
  conversation: ConversationSummary;
  initialMessages: MessageDto[];
}) {
  const [messages, setMessages] = useState(initialMessages);
  const [pending, setPending] = useState(false);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savedArtifacts, setSavedArtifacts] = useState<Record<string, ArtifactSummary>>({});
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const content = String(data.get("message") ?? "").trim();
    if (!content) return;

    setPending(true);
    setError(null);

    try {
      const result = await apiRequest<{
        userMessage: MessageDto;
        assistantMessage: MessageDto;
      }>(`/api/conversations/${conversation.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content, clientRequestId: crypto.randomUUID() })
      });
      setMessages((current) => [...current, result.userMessage, result.assistantMessage]);
      form.reset();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "CADRE could not complete the message.");
    } finally {
      setPending(false);
    }
  }

  async function saveMarkdown(message: MessageDto) {
    setSavingId(message.id);
    setError(null);

    try {
      const { artifact } = await apiRequest<{ artifact: ArtifactSummary }>("/api/artifacts", {
        method: "POST",
        body: JSON.stringify({
          conversationId: conversation.id,
          messageId: message.id,
          title: `${conversation.title} — CADRE response`
        })
      });
      setSavedArtifacts((current) => ({ ...current, [message.id]: artifact }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The artifact could not be created.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="chat-panel">
      <section aria-label="Conversation messages" className="message-stream">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <p className="section-label">Conversation ready</p>
            <h2>What should CADRE move forward?</h2>
            <p>
              State the objective, authority, and desired output. This conversation remains inside
              its selected workspace.
            </p>
          </div>
        ) : (
          messages.map((message) => {
            const savedArtifact = savedArtifacts[message.id];
            return (
              <article className={`message message-${message.role}`} key={message.id}>
                <header>
                  <strong>
                    {message.role === "user"
                      ? "You"
                      : message.role === "assistant"
                        ? "CADRE"
                        : message.role}
                  </strong>
                  <time dateTime={message.createdAt}>{messageTime(message.createdAt)}</time>
                </header>
                <div className="message-content">{message.content}</div>
                {message.role === "assistant" && (
                  <footer className="message-actions">
                    {savedArtifact ? (
                      <Link
                        className="button button-secondary"
                        href={`/app/artifacts/${savedArtifact.id}`}
                      >
                        Open saved artifact
                      </Link>
                    ) : (
                      <button
                        className="button button-secondary"
                        disabled={savingId === message.id}
                        onClick={() => saveMarkdown(message)}
                        type="button"
                      >
                        {savingId === message.id ? "Saving…" : "Save as Markdown"}
                      </button>
                    )}
                    {message.model && <span className="metadata">{message.model}</span>}
                  </footer>
                )}
              </article>
            );
          })
        )}
        <div ref={endRef} />
      </section>

      <form className="chat-composer" onSubmit={sendMessage}>
        <label className="field-label" htmlFor="chat-message">
          Message CADRE
        </label>
        <textarea
          autoFocus={messages.length === 0}
          className="textarea"
          disabled={pending}
          id="chat-message"
          maxLength={12_000}
          name="message"
          placeholder="Describe the objective and the exact result you need…"
          required
          rows={4}
        />
        <div className="composer-footer">
          <span className="metadata">Server-side provider · workspace-scoped history</span>
          <button className="button button-primary" disabled={pending} type="submit">
            {pending ? "Working…" : "Send message"}
          </button>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </form>
    </div>
  );
}
