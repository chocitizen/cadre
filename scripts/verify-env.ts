import { loadEnvConfig } from "@next/env";

loadEnvConfig(process.cwd(), process.env.NODE_ENV !== "production");

type Status = "PRESENT" | "DEFAULT" | "MISSING" | "MISCONFIGURED";

function secretStatus(value: string | undefined): Status {
  if (value === undefined || value.length === 0) return "MISSING";
  if (value.trim() !== value || value.length < 20 || /\s/.test(value)) return "MISCONFIGURED";
  return "PRESENT";
}

function modelStatus(value: string | undefined): Status {
  if (!value) return "MISSING";
  return /^[a-z0-9][a-z0-9._-]*$/i.test(value) ? "PRESENT" : "MISCONFIGURED";
}

function urlStatus(value: string | undefined, protocols: readonly string[]): Status {
  if (!value) return "MISSING";
  try {
    return protocols.includes(new URL(value).protocol) ? "PRESENT" : "MISCONFIGURED";
  } catch {
    return "MISCONFIGURED";
  }
}

const openAiKeyStatus = secretStatus(process.env.OPENAI_API_KEY);
const openAiModelStatus = process.env.OPENAI_MODEL
  ? modelStatus(process.env.OPENAI_MODEL)
  : "DEFAULT";
const appUrlStatus = process.env.APP_URL
  ? urlStatus(process.env.APP_URL, ["http:", "https:"])
  : process.env.NODE_ENV === "production"
    ? "MISSING"
    : "DEFAULT";
const databaseStatus = process.env.DATABASE_URL
  ? urlStatus(process.env.DATABASE_URL, ["postgres:", "postgresql:"])
  : "PRESENT";

console.log(`OPENAI_API_KEY: ${openAiKeyStatus}`);
console.log(`OPENAI_MODEL: ${openAiModelStatus}`);
console.log(`APP_URL: ${appUrlStatus}`);
console.log(`DATABASE: ${databaseStatus}`);

const providerId = process.env.AI_PROVIDER ?? process.env.CADRE_AI_PROVIDER ?? "openai";
const requiredValueMissing =
  (providerId === "openai" && openAiKeyStatus === "MISSING") ||
  (process.env.NODE_ENV === "production" && appUrlStatus === "MISSING");

if (
  requiredValueMissing ||
  [openAiKeyStatus, openAiModelStatus, appUrlStatus, databaseStatus].includes("MISCONFIGURED")
) {
  process.exitCode = 1;
}
