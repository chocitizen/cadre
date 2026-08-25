import type { AiGenerateRequest, AiGenerateResult, AiProvider } from "../contracts";

const DEFAULT_GATEWAY_URL = "http://127.0.0.1:4000";
const DEFAULT_MODEL = "cadre-free";
const DEFAULT_TIMEOUT_MS = 90_000;

type FetchImplementation = typeof fetch;

interface LiteLlmChatCompletion {
  readonly id?: unknown;
  readonly model?: unknown;
  readonly choices?: unknown;
  readonly usage?: unknown;
}

interface LiteLlmUsage {
  readonly prompt_tokens?: unknown;
  readonly completion_tokens?: unknown;
  readonly total_tokens?: unknown;
}

export interface LiteLlmProviderOptions {
  readonly apiKey?: string;
  readonly baseUrl?: string;
  readonly fetchImplementation?: FetchImplementation;
  readonly model?: string;
  readonly timeoutMs?: number;
}

export class AiGatewayError extends Error {
  readonly status: number | null;

  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = "AiGatewayError";
    this.status = status;
  }
}

function positiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

function isLoopbackHostname(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]";
}

function completionEndpoint(baseUrl: string): URL {
  let url: URL;

  try {
    url = new URL(baseUrl);
  } catch {
    throw new AiGatewayError("The AI gateway URL is invalid.");
  }

  if (!(["http:", "https:"] as const).includes(url.protocol as "http:" | "https:")) {
    throw new AiGatewayError("The AI gateway URL is invalid.");
  }

  if (url.protocol === "http:" && !isLoopbackHostname(url.hostname)) {
    throw new AiGatewayError("The AI gateway URL must use HTTPS unless it is loopback.");
  }

  if (url.username || url.password) {
    throw new AiGatewayError("The AI gateway URL must not contain credentials.");
  }

  const path = url.pathname.replace(/\/+$/, "");
  url.pathname = `${path.endsWith("/v1") ? path : `${path}/v1`}/chat/completions`;
  url.search = "";
  url.hash = "";
  return url;
}

function timeoutMs(value: number | undefined): number {
  if (value === undefined) return DEFAULT_TIMEOUT_MS;
  if (!Number.isSafeInteger(value) || value < 1_000 || value > 300_000) {
    throw new AiGatewayError("The AI gateway timeout is invalid.");
  }
  return value;
}

function contentFromCompletion(completion: LiteLlmChatCompletion): string {
  if (!Array.isArray(completion.choices)) {
    throw new AiGatewayError("The AI gateway returned an invalid response.");
  }

  const firstChoice = completion.choices[0];
  if (typeof firstChoice !== "object" || firstChoice === null || !("message" in firstChoice)) {
    throw new AiGatewayError("The AI gateway returned an invalid response.");
  }

  const message = firstChoice.message;
  if (typeof message !== "object" || message === null || !("content" in message)) {
    throw new AiGatewayError("The AI gateway returned an invalid response.");
  }

  const content = typeof message.content === "string" ? message.content.trim() : "";
  if (!content) {
    throw new AiGatewayError("The AI gateway returned no text output.");
  }
  return content;
}

function usageFromCompletion(completion: LiteLlmChatCompletion): AiGenerateResult["usage"] {
  if (typeof completion.usage !== "object" || completion.usage === null) return null;

  const usage = completion.usage as LiteLlmUsage;
  if (!positiveInteger(usage.prompt_tokens) || !positiveInteger(usage.completion_tokens)) {
    return null;
  }

  const calculatedTotal = usage.prompt_tokens + usage.completion_tokens;
  return {
    inputTokens: usage.prompt_tokens,
    outputTokens: usage.completion_tokens,
    totalTokens: positiveInteger(usage.total_tokens) ? usage.total_tokens : calculatedTotal
  };
}

export class LiteLlmProvider implements AiProvider {
  readonly id = "litellm";
  readonly defaultModel: string;
  readonly #apiKey: string | undefined;
  readonly #endpoint: URL;
  readonly #fetch: FetchImplementation;
  readonly #timeoutMs: number;

  constructor(options: LiteLlmProviderOptions = {}) {
    this.#apiKey = options.apiKey?.trim() || undefined;
    this.#endpoint = completionEndpoint(options.baseUrl?.trim() || DEFAULT_GATEWAY_URL);
    this.#fetch = options.fetchImplementation ?? fetch;
    this.#timeoutMs = timeoutMs(options.timeoutMs);
    this.defaultModel = options.model?.trim() || DEFAULT_MODEL;
  }

  async generate(request: AiGenerateRequest): Promise<AiGenerateResult> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.#timeoutMs);

    try {
      let response: Response;

      try {
        response = await this.#fetch(this.#endpoint, {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
            ...(this.#apiKey ? { Authorization: `Bearer ${this.#apiKey}` } : {})
          },
          body: JSON.stringify({
            model: request.model?.trim() || this.defaultModel,
            messages: [
              { role: "system", content: request.instructions },
              ...request.messages.map(({ role, content }) => ({
                role: role === "developer" ? "system" : role,
                content
              }))
            ],
            stream: false,
            user: request.safetyIdentifier,
            ...(request.maxOutputTokens === undefined
              ? {}
              : { max_tokens: request.maxOutputTokens })
          }),
          signal: controller.signal
        });
      } catch {
        throw new AiGatewayError(
          controller.signal.aborted
            ? "The AI gateway request timed out."
            : "The AI gateway is unavailable."
        );
      }

      if (!response.ok) {
        throw new AiGatewayError("The AI gateway rejected the request.", response.status);
      }

      let completion: LiteLlmChatCompletion;
      try {
        completion = (await response.json()) as LiteLlmChatCompletion;
      } catch {
        throw new AiGatewayError("The AI gateway returned an invalid response.", response.status);
      }

      const model = typeof completion.model === "string" ? completion.model.trim() : "";
      if (!model) {
        throw new AiGatewayError("The AI gateway returned an invalid model identifier.");
      }

      return {
        providerId: this.id,
        model,
        externalResponseId: typeof completion.id === "string" ? completion.id : null,
        text: contentFromCompletion(completion),
        usage: usageFromCompletion(completion)
      };
    } finally {
      clearTimeout(timer);
    }
  }
}
