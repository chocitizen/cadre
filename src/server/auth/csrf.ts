import { timingSafeEqual } from "node:crypto";

import { hashOpaqueToken } from "./session";

export class RequestSecurityError extends Error {
  readonly status = 403;
  readonly code: "ORIGIN_REJECTED" | "CSRF_REJECTED";

  constructor(code: "ORIGIN_REJECTED" | "CSRF_REJECTED", message: string) {
    super(message);
    this.name = "RequestSecurityError";
    this.code = code;
  }
}

function normalizedOrigin(value: string): string | null {
  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

export function assertSameOrigin(request: Request, configuredOrigin = process.env.APP_URL): void {
  const requestOrigin = request.headers.get("origin");
  const expectedOrigin = normalizedOrigin(configuredOrigin ?? request.url);
  const actualOrigin = requestOrigin ? normalizedOrigin(requestOrigin) : null;

  if (!expectedOrigin || !actualOrigin || actualOrigin !== expectedOrigin) {
    throw new RequestSecurityError("ORIGIN_REJECTED", "Request origin was not accepted.");
  }
}

export function verifyCsrfToken(
  expectedHash: string,
  suppliedToken: string | null | undefined
): boolean {
  if (
    !suppliedToken ||
    !/^[A-Za-z0-9_-]{40,}$/.test(suppliedToken) ||
    !/^[0-9a-f]{64}$/.test(expectedHash)
  ) {
    return false;
  }

  const actual = Buffer.from(hashOpaqueToken(suppliedToken), "hex");
  const expected = Buffer.from(expectedHash, "hex");
  return timingSafeEqual(actual, expected);
}

export function assertCsrf(request: Request, expectedHash: string): void {
  if (!verifyCsrfToken(expectedHash, request.headers.get("x-csrf-token"))) {
    throw new RequestSecurityError("CSRF_REJECTED", "CSRF token was not accepted.");
  }
}

export function assertMutationSecurity(
  request: Request,
  expectedCsrfHash: string,
  configuredOrigin?: string
): void {
  assertSameOrigin(request, configuredOrigin);
  assertCsrf(request, expectedCsrfHash);
}
