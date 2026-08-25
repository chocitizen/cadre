"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiRequest } from "@/lib/client-api";
import type { ConversationSummary } from "@/lib/types";

export function NewConversationForm({ workspaceId }: { workspaceId: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function createConversation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const form = new FormData(event.currentTarget);

    try {
      const { conversation } = await apiRequest<{ conversation: ConversationSummary }>(
        `/api/workspaces/${workspaceId}/conversations`,
        {
          method: "POST",
          body: JSON.stringify({ title: String(form.get("title") ?? "") })
        }
      );
      router.push(`/app/c/${conversation.id}`);
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The conversation could not be created.");
      setPending(false);
    }
  }

  return (
    <form className="new-conversation-form" onSubmit={createConversation}>
      <div className="field">
        <label className="field-label" htmlFor="conversation-title">
          Begin a governed conversation
        </label>
        <div className="inline-field">
          <input
            className="input"
            id="conversation-title"
            maxLength={120}
            name="title"
            placeholder="Objective or working title"
          />
          <button className="button button-primary" disabled={pending} type="submit">
            {pending ? "Opening…" : "Start"}
          </button>
        </div>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
