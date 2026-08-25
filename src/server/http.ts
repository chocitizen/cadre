import { randomUUID } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { ZodError, type ZodType } from "zod";

import { AuthorizationError } from "./auth/authorize";
import { RequestSecurityError } from "./auth/csrf";

export class HttpError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string
  ) {
    super(message);
    this.name = "HttpError";
  }
}

export function apiError(status: number, code: string, message: string) {
  return NextResponse.json({ error: { code, message } }, { status });
}

export async function parseJson<T>(request: NextRequest, schema: ZodType<T>): Promise<T> {
  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("application/json")) {
    throw new HttpError(415, "unsupported_media_type", "Use application/json for this request.");
  }

  let value: unknown;
  try {
    value = await request.json();
  } catch {
    throw new HttpError(400, "invalid_json", "The request body is not valid JSON.");
  }

  try {
    return schema.parse(value);
  } catch (cause) {
    if (cause instanceof ZodError) {
      throw new HttpError(422, "invalid_request", "The request contains invalid fields.");
    }
    throw cause;
  }
}

export function requestId(request: NextRequest): string {
  const incoming = request.headers.get("x-request-id")?.trim();
  return incoming && incoming.length <= 128 ? incoming : randomUUID();
}

export function handleApiError(cause: unknown): NextResponse {
  if (cause instanceof HttpError) {
    return apiError(cause.status, cause.code, cause.message);
  }

  if (cause instanceof AuthorizationError || cause instanceof RequestSecurityError) {
    return apiError(cause.status, cause.code.toLowerCase(), cause.message);
  }

  // Deliberately avoid logging request bodies, prompts, credentials, or provider payloads.
  console.error("CADRE request failed", {
    errorName: cause instanceof Error ? cause.name : "UnknownError"
  });
  return apiError(500, "internal_error", "CADRE could not complete the request.");
}
