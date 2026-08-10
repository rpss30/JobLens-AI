import { NextResponse } from "next/server";

/**
 * Liveness probe for the Next.js server itself. It deliberately does not call
 * FastAPI, so the container healthcheck reports on this process only and a
 * backend outage cannot restart a frontend that is serving fine. The sidebar
 * indicator is what reports backend reachability.
 */
export async function GET() {
  return NextResponse.json(
    { status: "ok" },
    { headers: { "Cache-Control": "no-store" } },
  );
}
