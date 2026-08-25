import { describe, expect, it } from "vitest";

import {
  createLiteLlmEnvironment,
  createLiteLlmInstallEnvironment
} from "../../scripts/litellm-environment";
import { createSafetyIdentifier } from "../../src/server/ai/contracts";
import { AiProviderRegistry, createProviderRegistry } from "../../src/server/ai/provider-registry";
import { LiteLlmProvider } from "../../src/server/ai/providers/litellm";
import { TestAiProvider } from "../../src/server/ai/providers/test";

const enabledEnvironment: NodeJS.ProcessEnv = {
  CADRE_ENABLE_TEST_PROVIDER: "true",
  NODE_ENV: "test"
};

describe("AI provider boundary", () => {
  it("creates a stable pseudonymous safety identifier", () => {
    const identifier = createSafetyIdentifier("owner-user-id");

    expect(identifier).toHaveLength(64);
    expect(identifier).toBe(createSafetyIdentifier("owner-user-id"));
    expect(identifier).not.toContain("owner-user-id");
  });

  it("keeps the test provider behind an explicit non-production gate", () => {
    expect(
      () =>
        new TestAiProvider({
          environment: {
            CADRE_ENABLE_TEST_PROVIDER: "true",
            NODE_ENV: "production"
          }
        })
    ).toThrow("requires CADRE_ENABLE_TEST_PROVIDER=true outside production");

    expect(() => new TestAiProvider({ environment: { NODE_ENV: "test" } })).toThrow(
      "requires CADRE_ENABLE_TEST_PROVIDER=true outside production"
    );

    expect(
      () =>
        new TestAiProvider({
          environment: {
            CADRE_ENABLE_TEST_PROVIDER: "true"
          } as unknown as NodeJS.ProcessEnv
        })
    ).toThrow("requires CADRE_ENABLE_TEST_PROVIDER=true outside production");
  });

  it("routes requests through the registered provider contract", async () => {
    const provider = new TestAiProvider({
      environment: enabledEnvironment,
      responseText: "Verified test output."
    });
    const registry = new AiProviderRegistry({
      providers: [provider],
      defaultProviderId: "test"
    });

    const result = await registry.resolve().generate({
      instructions: "Test instructions.",
      messages: [{ role: "user", content: "Test message." }],
      safetyIdentifier: createSafetyIdentifier("test-user")
    });

    expect(result).toMatchObject({
      providerId: "test",
      model: "cadre-test-v0.1",
      text: "Verified test output.",
      externalResponseId: null,
      usage: null
    });
  });

  it("defaults to LiteLLM without requiring an OpenAI credential", () => {
    const registry = createProviderRegistry({ NODE_ENV: "production" });

    expect(registry.list()).toEqual([{ id: "litellm", defaultModel: "cadre-free" }]);
    expect(registry.resolve().id).toBe("litellm");
  });

  it("passes only the active provider lane into the LiteLLM process", () => {
    const openRouterKey = ["OPENROUTER", "_API_KEY"].join("");
    const gatewayKey = ["CADRE_AI_GATEWAY", "_API_KEY"].join("");
    const directProviderKeys = [
      ["OPEN", "AI_API_KEY"].join(""),
      ["ANTHROPIC", "_API_KEY"].join(""),
      ["GEMINI", "_API_KEY"].join("")
    ];
    const source: NodeJS.ProcessEnv = {
      NODE_ENV: "test",
      PATH: "/usr/bin",
      LITELLM_MODE: "DEV",
      UNRELATED_SECRET: "must-not-be-forwarded"
    };
    source[openRouterKey] = "active-openrouter-test-token";
    source[gatewayKey] = "gateway-test-token";
    for (const key of directProviderKeys) source[key] = "inactive-provider-test-token";

    const environment = createLiteLlmEnvironment(source);

    expect(environment).toMatchObject({
      PATH: "/usr/bin",
      NODE_ENV: "production",
      LITELLM_MODE: "PRODUCTION",
      CADRE_OPENROUTER_MODEL: "openrouter/openrouter/free",
      OPENROUTER_API_BASE: "https://openrouter.ai/api/v1"
    });
    expect(environment[openRouterKey]).toBe("active-openrouter-test-token");
    expect(environment[gatewayKey]).toBe("gateway-test-token");
    for (const key of directProviderKeys) expect(environment).not.toHaveProperty(key);
    expect(environment).not.toHaveProperty("UNRELATED_SECRET");

    const installEnvironment = createLiteLlmInstallEnvironment(source);
    expect(installEnvironment).toMatchObject({ PATH: "/usr/bin", NODE_ENV: "production" });
    expect(installEnvironment).not.toHaveProperty(openRouterKey);
    expect(installEnvironment).not.toHaveProperty(gatewayKey);
    for (const key of directProviderKeys) expect(installEnvironment).not.toHaveProperty(key);
    expect(installEnvironment).not.toHaveProperty("UNRELATED_SECRET");
  });

  it("uses the server-side LiteLLM gateway contract and a pseudonymous user", async () => {
    const requests: Array<{ init: RequestInit; url: string }> = [];
    const fetchImplementation: typeof fetch = async (input, init) => {
      requests.push({
        init: init ?? {},
        url: input instanceof Request ? input.url : input.toString()
      });
      return new Response(
        JSON.stringify({
          id: "gateway-response-test",
          model: "provider/model-used",
          choices: [{ message: { role: "assistant", content: " Provider output. " } }],
          usage: {
            prompt_tokens: 4,
            completion_tokens: 2,
            total_tokens: 6
          }
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    };
    const provider = new LiteLlmProvider({
      apiKey: "gateway-test-token",
      baseUrl: "http://127.0.0.1:4000/v1/",
      fetchImplementation
    });
    const safetyIdentifier = createSafetyIdentifier("private-user-id");

    const result = await provider.generate({
      instructions: "Private instructions.",
      messages: [
        { role: "developer", content: "Private developer context." },
        { role: "user", content: "Private prompt." }
      ],
      safetyIdentifier,
      maxOutputTokens: 64
    });

    expect(requests).toHaveLength(1);
    expect(requests[0]?.url).toBe("http://127.0.0.1:4000/v1/chat/completions");
    expect(new Headers(requests[0]?.init.headers).get("Authorization")).toBe(
      "Bearer gateway-test-token"
    );
    expect(JSON.parse(String(requests[0]?.init.body))).toEqual({
      model: "cadre-free",
      messages: [
        { role: "system", content: "Private instructions." },
        { role: "system", content: "Private developer context." },
        { role: "user", content: "Private prompt." }
      ],
      stream: false,
      user: safetyIdentifier,
      max_tokens: 64
    });
    expect(result).toMatchObject({
      providerId: "litellm",
      model: "provider/model-used",
      externalResponseId: "gateway-response-test",
      text: "Provider output.",
      usage: { inputTokens: 4, outputTokens: 2, totalTokens: 6 }
    });
  });

  it("never requires or sends a gateway credential when authentication is disabled", async () => {
    let authorizationHeader: string | null = "unexpected";
    const fetchImplementation: typeof fetch = async (_input, init) => {
      authorizationHeader = new Headers(init?.headers).get("Authorization");
      return Response.json({
        id: "response-test",
        model: "provider/model-used",
        choices: [{ message: { content: "Provider output." } }]
      });
    };
    const provider = new LiteLlmProvider({ fetchImplementation });

    await provider.generate({
      instructions: "Instructions.",
      messages: [{ role: "user", content: "Prompt." }],
      safetyIdentifier: createSafetyIdentifier("test-user")
    });

    expect(authorizationHeader).toBeNull();
  });

  it("requires TLS for a non-loopback gateway", () => {
    expect(() => new LiteLlmProvider({ baseUrl: "http://gateway.example.test" })).toThrow(
      "must use HTTPS unless it is loopback"
    );
    expect(() => new LiteLlmProvider({ baseUrl: "http://[::1]:4000" })).not.toThrow();
  });

  it("redacts upstream failure details", async () => {
    const provider = new LiteLlmProvider({
      fetchImplementation: async () => new Response("sensitive upstream payload", { status: 429 })
    });

    const generation = provider.generate({
      instructions: "Instructions.",
      messages: [{ role: "user", content: "Prompt." }],
      safetyIdentifier: createSafetyIdentifier("test-user")
    });

    await expect(generation).rejects.toMatchObject({
      message: "The AI gateway rejected the request.",
      status: 429
    });
    await expect(generation).rejects.not.toThrow("sensitive upstream payload");
  });
});
