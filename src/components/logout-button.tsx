"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest } from "@/lib/client-api";

export function LogoutButton({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function logout() {
    setPending(true);
    try {
      await apiRequest<{ authenticated: false }>("/api/auth/logout", { method: "POST" });
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <button
      className="button button-quiet logout-button"
      disabled={pending}
      onClick={logout}
      type="button"
    >
      {pending ? "Closing…" : compact ? "Exit" : "Sign out"}
    </button>
  );
}
