const HOST_ENVIRONMENT_KEYS = [
  "ALL_PROXY",
  "CURL_CA_BUNDLE",
  "HOME",
  "HTTPS_PROXY",
  "HTTP_PROXY",
  "LANG",
  "LC_ALL",
  "LC_CTYPE",
  "NODE_EXTRA_CA_CERTS",
  "NO_PROXY",
  "PATH",
  "REQUESTS_CA_BUNDLE",
  "SSL_CERT_DIR",
  "SSL_CERT_FILE",
  "TEMP",
  "TMP",
  "TMPDIR",
  "all_proxy",
  "http_proxy",
  "https_proxy",
  "no_proxy"
] as const;

const ACTIVE_GATEWAY_KEYS = [
  "CADRE_AI_GATEWAY_API_KEY",
  "OPENROUTER_API_KEY",
  "OPENROUTER_API_BASE",
  "CADRE_OPENROUTER_MODEL",
  "OR_SITE_URL",
  "OR_APP_NAME"
] as const;

function copyDefined(
  target: NodeJS.ProcessEnv,
  source: NodeJS.ProcessEnv,
  keys: readonly string[]
): void {
  for (const key of keys) {
    const value = source[key];
    if (value !== undefined) target[key] = value;
  }
}

export function createLiteLlmEnvironment(source: NodeJS.ProcessEnv): NodeJS.ProcessEnv {
  const environment = createLiteLlmInstallEnvironment(source);
  copyDefined(environment, source, ACTIVE_GATEWAY_KEYS);

  return {
    ...environment,
    NODE_ENV: "production",
    LITELLM_MODE: "PRODUCTION",
    CADRE_OPENROUTER_MODEL: source.CADRE_OPENROUTER_MODEL?.trim() || "openrouter/openrouter/free",
    OPENROUTER_API_BASE: source.OPENROUTER_API_BASE?.trim() || "https://openrouter.ai/api/v1"
  };
}

export function createLiteLlmInstallEnvironment(source: NodeJS.ProcessEnv): NodeJS.ProcessEnv {
  const environment: NodeJS.ProcessEnv = { NODE_ENV: "production" };
  copyDefined(environment, source, HOST_ENVIRONMENT_KEYS);
  return environment;
}
