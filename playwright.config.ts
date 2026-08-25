import { defineConfig, devices } from "@playwright/test";

const port = 3100;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"], channel: "chrome" } },
    { name: "mobile", use: { ...devices["Pixel 7"], channel: "chrome" } }
  ],
  webServer: {
    command: `npm run db:prepare:e2e && npm run dev -- --hostname 127.0.0.1 --port ${port}`,
    url: `http://127.0.0.1:${port}/api/health/ready`,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      CADRE_DB_PATH: "./data/e2e",
      APP_URL: `http://127.0.0.1:${port}`,
      CADRE_AI_PROVIDER: "test",
      CADRE_ENABLE_TEST_PROVIDER: "true"
    }
  }
});
