import { and, desc, eq, inArray, lte } from "drizzle-orm";

import { getDatabase } from "../db/client";
import {
  conversations,
  messages,
  workspaceMemberships,
  workspaces,
  type Message
} from "../db/schema";
import { createSafetyIdentifier, type AiGenerateResult, type AiMessage } from "./contracts";
import {
  CADRE_CHAT_PROMPT_KEY,
  CADRE_CHAT_PROMPT_VERSION,
  renderCadreChatInstructions
} from "./prompts";
import { AiProviderRegistry, createProviderRegistry } from "./provider-registry";

const MAX_CHAT_MESSAGE_CHARACTERS = 32_000;
const MAX_PROVIDER_HISTORY_MESSAGES = 50;

export interface SendChatMessageInput {
  readonly conversationId: string;
  readonly workspaceId: string;
  readonly userId: string;
  readonly content: string;
  readonly clientRequestId?: string | null;
  readonly providerId?: string;
  readonly model?: string;
  readonly maxOutputTokens?: number;
  readonly canonicalContext?: readonly string[];
  readonly providerRegistry?: AiProviderRegistry;
}

export interface SendChatMessageResult {
  readonly userMessage: Message;
  readonly assistantMessage: Message;
  readonly generation: AiGenerateResult;
}

function validateMessageContent(content: string): string {
  const normalizedContent = content.trim();

  if (!normalizedContent) {
    throw new Error("A chat message is required.");
  }

  if (normalizedContent.length > MAX_CHAT_MESSAGE_CHARACTERS) {
    throw new Error(`Chat messages cannot exceed ${MAX_CHAT_MESSAGE_CHARACTERS} characters.`);
  }

  return normalizedContent;
}

function storedGeneration(message: Message): AiGenerateResult | null {
  if (
    message.status !== "completed" ||
    !message.provider ||
    !message.model ||
    !message.contentText
  ) {
    return null;
  }

  const inputTokens = message.inputTokens ?? 0;
  const outputTokens = message.outputTokens ?? 0;

  return {
    providerId: message.provider,
    model: message.model,
    externalResponseId: message.providerResponseId,
    text: message.contentText,
    usage:
      message.inputTokens === null && message.outputTokens === null
        ? null
        : {
            inputTokens,
            outputTokens,
            totalTokens: inputTokens + outputTokens
          }
  };
}

export async function sendChatMessage(input: SendChatMessageInput): Promise<SendChatMessageResult> {
  const content = validateMessageContent(input.content);
  const db = await getDatabase();
  const [authorizedContext] = await db
    .select({ conversation: conversations, workspace: workspaces })
    .from(conversations)
    .innerJoin(
      workspaces,
      and(eq(workspaces.id, conversations.workspaceId), eq(workspaces.status, "active"))
    )
    .innerJoin(
      workspaceMemberships,
      and(
        eq(workspaceMemberships.workspaceId, conversations.workspaceId),
        eq(workspaceMemberships.userId, input.userId)
      )
    )
    .where(
      and(
        eq(conversations.id, input.conversationId),
        eq(conversations.workspaceId, input.workspaceId),
        eq(conversations.status, "active")
      )
    )
    .limit(1);

  if (!authorizedContext) {
    throw new Error("The conversation is unavailable.");
  }

  const clientRequestId = input.clientRequestId?.trim() || null;

  if (clientRequestId) {
    const [existingUserMessage] = await db
      .select()
      .from(messages)
      .where(
        and(
          eq(messages.conversationId, input.conversationId),
          eq(messages.clientRequestId, clientRequestId),
          eq(messages.role, "user")
        )
      )
      .limit(1);

    if (existingUserMessage) {
      const [existingAssistantMessage] = await db
        .select()
        .from(messages)
        .where(
          and(
            eq(messages.conversationId, input.conversationId),
            eq(messages.sequence, existingUserMessage.sequence + 1),
            eq(messages.role, "assistant")
          )
        )
        .limit(1);
      const existingGeneration = existingAssistantMessage
        ? storedGeneration(existingAssistantMessage)
        : null;

      if (existingAssistantMessage && existingGeneration) {
        return {
          userMessage: existingUserMessage,
          assistantMessage: existingAssistantMessage,
          generation: existingGeneration
        };
      }

      throw new Error("This chat request is already pending or failed.");
    }
  }

  const [latestMessage] = await db
    .select({ sequence: messages.sequence })
    .from(messages)
    .where(eq(messages.conversationId, input.conversationId))
    .orderBy(desc(messages.sequence))
    .limit(1);
  const userSequence = (latestMessage?.sequence ?? 0) + 1;

  const storedPair = await db.transaction(async (transaction) => {
    const [userMessage] = await transaction
      .insert(messages)
      .values({
        workspaceId: input.workspaceId,
        conversationId: input.conversationId,
        sequence: userSequence,
        role: "user",
        contentText: content,
        createdByUserId: input.userId,
        status: "completed",
        clientRequestId
      })
      .returning();
    const [assistantMessage] = await transaction
      .insert(messages)
      .values({
        workspaceId: input.workspaceId,
        conversationId: input.conversationId,
        sequence: userSequence + 1,
        role: "assistant",
        contentText: "",
        status: "pending",
        promptKey: CADRE_CHAT_PROMPT_KEY,
        promptVersion: CADRE_CHAT_PROMPT_VERSION
      })
      .returning();

    if (!userMessage || !assistantMessage) {
      throw new Error("The conversation messages were not persisted.");
    }

    return { userMessage, assistantMessage };
  });

  const recentMessages = await db
    .select({ role: messages.role, contentText: messages.contentText })
    .from(messages)
    .where(
      and(
        eq(messages.conversationId, input.conversationId),
        eq(messages.status, "completed"),
        inArray(messages.role, ["user", "assistant", "system"]),
        lte(messages.sequence, userSequence)
      )
    )
    .orderBy(desc(messages.sequence))
    .limit(MAX_PROVIDER_HISTORY_MESSAGES);
  const providerMessages: AiMessage[] = recentMessages.reverse().map(({ role, contentText }) => ({
    role: role as AiMessage["role"],
    content: contentText
  }));

  try {
    const registry = input.providerRegistry ?? createProviderRegistry();
    const provider = registry.resolve(input.providerId);
    const generation = await provider.generate({
      instructions: renderCadreChatInstructions({
        workspaceId: authorizedContext.workspace.id,
        workspaceName: authorizedContext.workspace.name,
        canonicalContext: input.canonicalContext
      }),
      messages: providerMessages,
      safetyIdentifier: createSafetyIdentifier(input.userId),
      model: input.model,
      maxOutputTokens: input.maxOutputTokens
    });
    const now = new Date();
    const [assistantMessage] = await db
      .update(messages)
      .set({
        contentText: generation.text,
        status: "completed",
        provider: generation.providerId,
        model: generation.model,
        providerResponseId: generation.externalResponseId,
        inputTokens: generation.usage?.inputTokens ?? null,
        outputTokens: generation.usage?.outputTokens ?? null,
        updatedAt: now
      })
      .where(and(eq(messages.id, storedPair.assistantMessage.id), eq(messages.status, "pending")))
      .returning();

    if (!assistantMessage) {
      throw new Error("The assistant message changed concurrently; reload the conversation.");
    }

    await db
      .update(conversations)
      .set({
        provider: generation.providerId,
        model: generation.model,
        lastMessageAt: now,
        updatedAt: now
      })
      .where(
        and(
          eq(conversations.id, input.conversationId),
          eq(conversations.workspaceId, input.workspaceId)
        )
      );

    return {
      userMessage: storedPair.userMessage,
      assistantMessage,
      generation
    };
  } catch {
    await db
      .update(messages)
      .set({
        contentText: "The AI response is unavailable. Please retry safely.",
        status: "failed",
        updatedAt: new Date()
      })
      .where(and(eq(messages.id, storedPair.assistantMessage.id), eq(messages.status, "pending")));

    throw new Error("AI response generation failed.");
  }
}
