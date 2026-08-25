import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

import { loadEnvConfig } from "@next/env";

import { createLiteLlmEnvironment } from "./litellm-environment";

const workspace = process.cwd();
loadEnvConfig(workspace, true);

const executable = join(workspace, ".venv-litellm", "bin", "litellm");
if (!existsSync(executable)) {
  console.error("LiteLLM is not installed. Run npm run ai:gateway:install first.");
  process.exit(1);
}

const environment = createLiteLlmEnvironment(process.env);

const result = spawnSync(
  executable,
  [
    "--config",
    join(workspace, "config", "litellm.yaml"),
    "--host",
    "127.0.0.1",
    "--port",
    "4000",
    "--num_workers",
    "1",
    "--telemetry",
    "False"
  ],
  { cwd: workspace, env: environment, stdio: "inherit" }
);

if (result.error || result.status !== 0) {
  process.exit(result.status ?? 1);
}
