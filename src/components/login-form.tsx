"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/client-api";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);

    const data = new FormData(event.currentTarget);

    try {
      await apiRequest<{ authenticated: true }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: String(data.get("email") ?? ""),
          password: String(data.get("password") ?? "")
        })
      });
      router.replace("/app");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Sign-in failed.");
      setPending(false);
    }
  }

  return (
    <form className="login-form" onSubmit={handleSubmit} noValidate>
      <div className="field">
        <label htmlFor="email">Email</label>
        <input
          className="input"
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          inputMode="email"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="password">Password</label>
        <input
          className="input"
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          minLength={14}
          required
        />
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button className="button button-primary" disabled={pending} type="submit">
        {pending ? "Verifying…" : "Enter CADRE"}
      </button>
    </form>
  );
}
