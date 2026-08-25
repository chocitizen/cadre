import type { ApiError } from "@/lib/types";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  const entry = document.cookie.split("; ").find((part) => part.startsWith(prefix));
  return entry ? decodeURIComponent(entry.slice(prefix.length)) : null;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const method = (init.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrfToken = readCookie("cadre_csrf");
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(path, {
    ...init,
    headers,
    credentials: "same-origin",
    cache: "no-store"
  });

  if (response.status === 401 && path !== "/api/auth/login") {
    window.location.assign(new URL("/login", window.location.origin).toString());
    throw new Error("Authentication required");
  }

  if (!response.ok) {
    const fallback = {
      error: { code: "request_failed", message: "The request could not be completed." }
    };
    const payload = (await response.json().catch(() => fallback)) as ApiError;
    throw new Error(payload.error?.message ?? fallback.error.message);
  }

  return (await response.json()) as T;
}
