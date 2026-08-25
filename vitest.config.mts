import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
    exclude:
      process.env.RUN_OPENAI_LIVE_TEST === "true" ? [] : ["tests/integration/openai-live.test.ts"],
    coverage: {
      reporter: ["text", "json", "html"]
    }
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url))
    }
  }
});
