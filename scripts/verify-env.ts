import { loadEnvConfig } from "@next/env";

loadEnvConfig(process.cwd(), process.env.NODE_ENV !== "production");

type Status = "PRESENT" | "DEFAULT" | "MISSING" | "MISCONFIGURED";

function secretStatus(value: string | undefined): Status {
  if (value === undefined || value.length === 0) return "MISSING";
  if (value.trim() !== value || value.length < 16 || /\s/.test(value)) return "MISCONFIGURED";
  return "PRESENT";
}

function modelStatus(value: string | undefined): Status {
  if (!value) return "MISSING";
  return /^[a-z0-9][a-z0-9._:/-]*$/i.test(value) ? "PRESENT" : "MISCONFIGURED";
}

function urlStatus(value: string | undefined, protocols: readonly string[]): Status {
  if (!value) return "MISSING";
  try {
    const url = new URL(value);
    if (url.username || url.password) return "MISCONFIGURED";
    return protocols.includes(url.protocol) ? "PRESENT" : "MISCONFIGURED";
  } catch {
    return "MISCONFIGURED";
  }
}

function timeoutStatus(value: string | undefined): Status {
  if (!value) return "DEFAULT";
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 1_000 && parsed <= 300_000
    ? "PRESENT"
    : "MISCONFIGURED";
}

function isLoopbackHostname(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "[::1]";
}

function aiGatewayUrlStatus(value: string): Status {
  const status = urlStatus(value, ["http:", "https:"]);
  if (status !== "PRESENT") return status;

  const url = new URL(value);
  return url.protocol === "http:" && !isLoopbackHostname(url.hostname)
    ? "MISCONFIGURED"
    : "PRESENT";
}

function defaultedStatus(value: string | undefined, validate: (value: string) => Status): Status {
  return value ? validate(value) : "DEFAULT";
}

function isLoopbackUrl(value: string): boolean {
  try {
    const hostname = new URL(value).hostname;
    return isLoopbackHostname(hostname);
  } catch {
    return false;
  }
}

const providerId =
  process.env.CADRE_AI_PROVIDER?.trim() || process.env.AI_PROVIDER?.trim() || "litellm";
const providerStatus: Status =
  providerId === "litellm" ||
  (providerId === "test" &&
    process.env.CADRE_ENABLE_TEST_PROVIDER === "true" &&
    process.env.NODE_ENV !== "production")
    ? process.env.CADRE_AI_PROVIDER || process.env.AI_PROVIDER
      ? "PRESENT"
      : "DEFAULT"
    : "MISCONFIGURED";

const gatewayUrl = process.env.CADRE_AI_GATEWAY_URL?.trim() || "http://127.0.0.1:4000";
const gatewayUrlStatus = defaultedStatus(process.env.CADRE_AI_GATEWAY_URL, aiGatewayUrlStatus);
const gatewayKeyStatus = secretStatus(process.env.CADRE_AI_GATEWAY_API_KEY);
const gatewayModelStatus = process.env.CADRE_AI_MODEL
  ? modelStatus(process.env.CADRE_AI_MODEL)
  : "DEFAULT";
const gatewayTimeoutStatus = timeoutStatus(process.env.CADRE_AI_TIMEOUT_MS);
const openRouterKeyStatus = secretStatus(process.env.OPENROUTER_API_KEY);
const openRouterBaseStatus = defaultedStatus(process.env.OPENROUTER_API_BASE, (value) =>
  urlStatus(value, ["https:"])
);
const openRouterModelStatus = process.env.CADRE_OPENROUTER_MODEL
  ? modelStatus(process.env.CADRE_OPENROUTER_MODEL)
  : "DEFAULT";
const appUrlStatus = process.env.APP_URL
  ? urlStatus(process.env.APP_URL, ["http:", "https:"])
  : process.env.NODE_ENV === "production"
    ? "MISSING"
    : "DEFAULT";
const databaseStatus = process.env.DATABASE_URL
  ? urlStatus(process.env.DATABASE_URL, ["postgres:", "postgresql:"])
  : "PRESENT";

console.log(`CADRE_AI_PROVIDER: ${providerStatus}`);
console.log(`CADRE_AI_GATEWAY_URL: ${gatewayUrlStatus}`);
console.log(`CADRE_AI_GATEWAY_API_KEY: ${gatewayKeyStatus}`);
console.log(`CADRE_AI_MODEL: ${gatewayModelStatus}`);
console.log(`CADRE_AI_TIMEOUT_MS: ${gatewayTimeoutStatus}`);
console.log(`OPENROUTER_API_KEY: ${openRouterKeyStatus}`);
console.log(`OPENROUTER_API_BASE: ${openRouterBaseStatus}`);
console.log(`CADRE_OPENROUTER_MODEL: ${openRouterModelStatus}`);
console.log(`OPENAI_API_KEY (optional/inactive): ${secretStatus(process.env.OPENAI_API_KEY)}`);
console.log(
  `ANTHROPIC_API_KEY (optional/inactive): ${secretStatus(process.env.ANTHROPIC_API_KEY)}`
);
console.log(`GEMINI_API_KEY (optional/inactive): ${secretStatus(process.env.GEMINI_API_KEY)}`);
console.log(`APP_URL: ${appUrlStatus}`);
console.log(`DATABASE: ${databaseStatus}`);

const remoteGatewayWithoutAuthentication =
  process.env.NODE_ENV === "production" &&
  providerId === "litellm" &&
  !isLoopbackUrl(gatewayUrl) &&
  gatewayKeyStatus !== "PRESENT";
const requiredValueMissing =
  (process.env.NODE_ENV === "production" && appUrlStatus === "MISSING") ||
  remoteGatewayWithoutAuthentication;
const configuredStatuses = [
  providerStatus,
  gatewayUrlStatus,
  gatewayKeyStatus,
  gatewayModelStatus,
  gatewayTimeoutStatus,
  openRouterKeyStatus,
  openRouterBaseStatus,
  openRouterModelStatus,
  appUrlStatus,
  databaseStatus,
  secretStatus(process.env.OPENAI_API_KEY),
  secretStatus(process.env.ANTHROPIC_API_KEY),
  secretStatus(process.env.GEMINI_API_KEY)
];

if (requiredValueMissing || configuredStatuses.includes("MISCONFIGURED")) {
  process.exitCode = 1;
}
