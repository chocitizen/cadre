import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

import { createLiteLlmInstallEnvironment } from "./litellm-environment";

const workspace = process.cwd();
const environmentDirectory = join(workspace, ".venv-litellm");
const environmentPython = join(environmentDirectory, "bin", "python");
const requestedPython = process.env.CADRE_PYTHON?.trim() || "python3";
const installationEnvironment = createLiteLlmInstallEnvironment(process.env);

function run(command: string, args: readonly string[]): void {
  const result = spawnSync(command, args, {
    cwd: workspace,
    env: installationEnvironment,
    stdio: "inherit"
  });

  if (result.error || result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function pythonVersion(command: string): [number, number] | null {
  const result = spawnSync(
    command,
    ["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
    { cwd: workspace, encoding: "utf8", env: installationEnvironment }
  );

  if (result.error || result.status !== 0) return null;
  const match = result.stdout.trim().match(/^(\d+)\.(\d+)$/);
  return match ? [Number(match[1]), Number(match[2])] : null;
}

const selectedPython = existsSync(environmentPython) ? environmentPython : requestedPython;
const version = pythonVersion(selectedPython);

if (!version || version[0] !== 3 || version[1] < 10 || version[1] >= 15) {
  console.error(
    "LiteLLM 1.95.0 requires Python 3.10 through 3.14. Set CADRE_PYTHON to an approved Python executable and retry."
  );
  process.exit(1);
}

if (!existsSync(environmentPython)) {
  run(selectedPython, ["-m", "venv", environmentDirectory]);
}

run(environmentPython, [
  "-m",
  "pip",
  "install",
  "--disable-pip-version-check",
  "--requirement",
  join(workspace, "requirements-litellm.txt")
]);

console.log("LiteLLM gateway runtime installed in the ignored local environment.");
