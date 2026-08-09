import { NextResponse } from "next/server";

import { ApiError, getApiBaseUrl } from "@/lib/api/client";
import type { AnalyzeRequest } from "@/lib/api/types";

const ALLOWED_FORMATS = new Set(["markdown", "pdf"]);

/**
 * Streams the generated report straight through so the browser can download it
 * without the file ever passing through client-side state.
 */
export async function POST(request: Request) {
  const requestedFormat =
    new URL(request.url).searchParams.get("format") ?? "markdown";

  if (!ALLOWED_FORMATS.has(requestedFormat)) {
    return NextResponse.json(
      { detail: "Report format must be markdown or pdf." },
      { status: 400 },
    );
  }

  let body: AnalyzeRequest;

  try {
    body = (await request.json()) as AnalyzeRequest;
  } catch {
    return NextResponse.json(
      { detail: "Request body must be valid JSON." },
      { status: 400 },
    );
  }

  let upstreamResponse: Response;

  try {
    upstreamResponse = await fetch(
      `${getApiBaseUrl()}/reports/candidate?format=${requestedFormat}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );
  } catch {
    return NextResponse.json(
      { detail: new ApiError("Could not reach the JobLens API.", 503).message },
      { status: 503 },
    );
  }

  if (!upstreamResponse.ok) {
    const detail = await upstreamResponse
      .json()
      .then((payload: { detail?: string }) => payload.detail)
      .catch(() => undefined);

    return NextResponse.json(
      { detail: detail ?? "The report could not be generated." },
      { status: upstreamResponse.status },
    );
  }

  return new Response(upstreamResponse.body, {
    headers: {
      "Content-Type":
        upstreamResponse.headers.get("content-type") ??
        "application/octet-stream",
      "Content-Disposition":
        upstreamResponse.headers.get("content-disposition") ?? "attachment",
    },
  });
}
