import { describe, expect, it } from "vitest";

import {
  RequestSecurityError,
  assertMutationSecurity,
  assertSameOrigin,
  verifyCsrfToken
} from "../../src/server/auth/csrf";
import { assertPasswordPolicy, hashPassword, verifyPassword } from "../../src/server/auth/password";
import {
  createOpaqueToken,
  getSessionCookieName,
  getSessionCookieOptions,
  hashOpaqueToken
} from "../../src/server/auth/session";

describe("password security", () => {
  it("hashes and verifies without retaining the plaintext", async () => {
    const password = "a sovereign passphrase with length";
    const encoded = await hashPassword(password);

    expect(encoded).toMatch(/^scrypt\$/);
    expect(encoded).not.toContain(password);
    await expect(verifyPassword(password, encoded)).resolves.toBe(true);
    await expect(verifyPassword(`${password}!`, encoded)).resolves.toBe(false);
  });

  it("enforces the minimum password policy", () => {
    expect(() => assertPasswordPolicy("too-short")).toThrow(/at least/);
  });
});

describe("session and request security", () => {
  it("hashes opaque tokens and validates CSRF tokens in constant-length form", () => {
    const token = createOpaqueToken();
    const tokenHash = hashOpaqueToken(token);

    expect(token).not.toBe(tokenHash);
    expect(tokenHash).toMatch(/^[0-9a-f]{64}$/);
    expect(verifyCsrfToken(tokenHash, token)).toBe(true);
    expect(verifyCsrfToken(tokenHash, `${token}x`)).toBe(false);
  });

  it("requires an exact origin and valid CSRF header", () => {
    const csrfToken = createOpaqueToken();
    const request = new Request("https://cadre.example/api/test", {
      method: "POST",
      headers: { origin: "https://cadre.example", "x-csrf-token": csrfToken }
    });

    expect(() =>
      assertMutationSecurity(request, hashOpaqueToken(csrfToken), "https://cadre.example")
    ).not.toThrow();
    expect(() => assertSameOrigin(request, "https://attacker.example")).toThrow(
      RequestSecurityError
    );
  });

  it("uses host-only secure cookie settings in production", () => {
    expect(getSessionCookieName(true)).toBe("__Host-cadre_session");
    expect(getSessionCookieOptions(true)).toMatchObject({
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      path: "/"
    });
  });
});
