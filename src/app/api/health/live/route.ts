import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET() {
  return NextResponse.json(
    { service: "cadre", status: "live" },
    { headers: { "Cache-Control": "no-store" } }
  );
}
