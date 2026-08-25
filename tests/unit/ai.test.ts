import { describe, expect, it } from "vitest";

import { createSafetyIdentifier } from "../../src/server/ai/contracts";
import { AiProviderRegistry } from "../../src/server/ai/provider-registry";
import { OpenAiProvider } from "../../src/server/ai/providers/openai";
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

  it("keeps OpenAI stateless and sends only a pseudonymous safety identifier", async () => {
    const requests: Array<Record<string, unknown>> = [];
    const provider = new OpenAiProvider({
      client: {
        responses: {
          create: async (request: Record<string, unknown>) => {
            requests.push(request);
            return {
              id: "response-test",
              model: "gpt-5.6-sol",
              output_text: "Provider output.",
              usage: {
                input_tokens: 4,
                output_tokens: 2,
                total_tokens: 6
              }
            };
          }
        }
      } as never
    });
    const safetyIdentifier = createSafetyIdentifier("private-user-id");

    const result = await provider.generate({
      instructions: "Private instructions.",
      messages: [{ role: "user", content: "Private prompt." }],
      safetyIdentifier
    });

    expect(requests).toHaveLength(1);
    expect(requests[0]).toMatchObject({
      model: "gpt-5.6",
      store: false,
      safety_identifier: safetyIdentifier
    });
    expect(requests[0]).not.toHaveProperty("user");
    expect(result).toMatchObject({
      providerId: "openai",
      model: "gpt-5.6-sol",
      externalResponseId: "response-test",
      text: "Provider output.",
      usage: { inputTokens: 4, outputTokens: 2, totalTokens: 6 }
    });
  });
});
