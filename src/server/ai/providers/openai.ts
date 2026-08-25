import OpenAI from "openai";

import type { AiGenerateRequest, AiGenerateResult, AiProvider } from "../contracts";

export interface OpenAiProviderOptions {
  readonly apiKey?: string;
  readonly model?: string;
  readonly client?: OpenAI;
}

export class OpenAiProvider implements AiProvider {
  readonly id = "openai";
  readonly defaultModel: string;
  readonly #apiKey: string | undefined;
  #client: OpenAI | undefined;

  constructor(options: OpenAiProviderOptions = {}) {
    this.#apiKey = options.apiKey?.trim() || undefined;
    this.#client = options.client;
    this.defaultModel = options.model?.trim() || "gpt-5.6";
  }

  async generate(request: AiGenerateRequest): Promise<AiGenerateResult> {
    const response = await this.#getClient().responses.create({
      model: request.model?.trim() || this.defaultModel,
      instructions: request.instructions,
      input: request.messages.map(({ role, content }) => ({ role, content })),
      store: false,
      safety_identifier: request.safetyIdentifier,
      ...(request.maxOutputTokens === undefined
        ? {}
        : { max_output_tokens: request.maxOutputTokens })
    });

    const text = response.output_text.trim();

    if (!text) {
      throw new Error("The AI provider returned no text output.");
    }

    return {
      providerId: this.id,
      model: response.model,
      externalResponseId: response.id,
      text,
      usage: response.usage
        ? {
            inputTokens: response.usage.input_tokens,
            outputTokens: response.usage.output_tokens,
            totalTokens: response.usage.total_tokens
          }
        : null
    };
  }

  #getClient(): OpenAI {
    if (this.#client) {
      return this.#client;
    }

    if (!this.#apiKey) {
      throw new Error("The OpenAI provider is not configured.");
    }

    this.#client = new OpenAI({ apiKey: this.#apiKey });
    return this.#client;
  }
}
