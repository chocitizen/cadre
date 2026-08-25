import { createHash } from "node:crypto";

export const AI_MESSAGE_ROLES = ["system", "developer", "user", "assistant"] as const;

export type AiMessageRole = (typeof AI_MESSAGE_ROLES)[number];

export interface AiMessage {
  readonly role: AiMessageRole;
  readonly content: string;
}

export interface AiGenerateRequest {
  readonly instructions: string;
  readonly messages: readonly AiMessage[];
  readonly safetyIdentifier: string;
  readonly model?: string;
  readonly maxOutputTokens?: number;
}

export interface AiTokenUsage {
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly totalTokens: number;
}

export interface AiGenerateResult {
  readonly providerId: string;
  readonly model: string;
  readonly externalResponseId: string | null;
  readonly text: string;
  readonly usage: AiTokenUsage | null;
}

export interface AiProvider {
  readonly id: string;
  readonly defaultModel: string;
  generate(request: AiGenerateRequest): Promise<AiGenerateResult>;
}

export function createSafetyIdentifier(subjectId: string): string {
  const normalizedSubjectId = subjectId.trim();

  if (!normalizedSubjectId) {
    throw new Error("A subject identifier is required.");
  }

  return createHash("sha256").update(`cadre:safety:v1:${normalizedSubjectId}`).digest("hex");
}
