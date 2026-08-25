import { NextResponse } from "next/server";

import { getDatabaseClient } from "@/server/db";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    const client = await getDatabaseClient();
    const rows = await client.query<{ id: string } & Record<string, unknown>>(
      "SELECT id FROM cadre_schema_migrations WHERE id = '0002_ready_dock_action_path' LIMIT 1"
    );

    if (rows[0]?.id !== "0002_ready_dock_action_path") {
      throw new Error("Required database migration is not present.");
    }

    return NextResponse.json(
      { checks: { database: "ready" }, service: "cadre", status: "ready" },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return NextResponse.json(
      { checks: { database: "unavailable" }, service: "cadre", status: "unavailable" },
      { status: 503, headers: { "Cache-Control": "no-store", "Retry-After": "5" } }
    );
  }
}
