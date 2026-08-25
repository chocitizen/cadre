import { loadEnvConfig } from "@next/env";
import { describe, expect, it } from "vitest";

import { createSafetyIdentifier } from "../../src/server/ai/contracts";
import { OpenAiProvider } from "../../src/server/ai/providers/openai";

loadEnvConfig(process.cwd(), true);

const liveEnabled = process.env.RUN_OPENAI_LIVE_TEST === "true";

describe.skipIf(!liveEnabled)("OpenAI live provider boundary", () => {
  it("returns a stateless server-side response without exposing credentials", async () => {
    expect(process.env.OPENAI_API_KEY).toBeTruthy();

    let result;
    try {
      result = await new OpenAiProvider({
        apiKey: process.env.OPENAI_API_KEY,
        model: process.env.OPENAI_MODEL
      }).generate({
        instructions: "Return only a short acknowledgement.",
        messages: [{ role: "user", content: "Confirm CADRE provider readiness." }],
        safetyIdentifier: createSafetyIdentifier("cadre-live-readiness-check"),
        maxOutputTokens: 64
      });
    } catch (cause) {
      const status =
        typeof cause === "object" && cause !== null && "status" in cause
          ? String(cause.status)
          : "unknown";
      throw new Error(`OpenAI live readiness failed with status ${status}.`);
    }

    expect(result.providerId).toBe("openai");
    expect(result.model.length).toBeGreaterThan(0);
    expect(result.text.length).toBeGreaterThan(0);
  }, 60_000);
});
