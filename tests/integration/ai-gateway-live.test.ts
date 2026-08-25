import { loadEnvConfig } from "@next/env";
import { describe, expect, it } from "vitest";

import { createSafetyIdentifier } from "../../src/server/ai/contracts";
import { createProviderRegistry } from "../../src/server/ai/provider-registry";
import { AiGatewayError } from "../../src/server/ai/providers/litellm";

loadEnvConfig(process.cwd(), true);

const liveEnabled = process.env.RUN_AI_GATEWAY_LIVE_TEST === "true";

describe.skipIf(!liveEnabled)("CADRE AI gateway live boundary", () => {
  it("returns a server-side response through the configured gateway", async () => {
    let result;
    try {
      result = await createProviderRegistry()
        .resolve()
        .generate({
          instructions: "Return only a short acknowledgement.",
          messages: [{ role: "user", content: "Confirm CADRE AI gateway readiness." }],
          safetyIdentifier: createSafetyIdentifier("cadre-live-readiness-check"),
          maxOutputTokens: 16
        });
    } catch (cause) {
      const status = cause instanceof AiGatewayError ? (cause.status ?? "unavailable") : "unknown";
      throw new Error(`CADRE AI gateway live readiness failed with status ${status}.`);
    }

    expect(result.providerId).toBe("litellm");
    expect(result.model.length).toBeGreaterThan(0);
    expect(result.text.length).toBeGreaterThan(0);
  }, 120_000);
});
