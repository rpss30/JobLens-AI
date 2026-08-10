import { NextResponse } from "next/server";

import { ApiError } from "@/lib/api/client";
import { analyzeJobs } from "@/lib/api/endpoints";
import type { AnalyzeRequest } from "@/lib/api/types";

/**
 * Thin proxy so the browser never needs the FastAPI origin. The body is
 * forwarded unchanged; FastAPI owns all validation and analysis.
 */
export async function POST(request: Request) {
  let body: AnalyzeRequest;

  try {
    body = (await request.json()) as AnalyzeRequest;
  } catch {
    return NextResponse.json(
      { detail: "Request body must be valid JSON." },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await analyzeJobs(body));
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Analysis failed unexpectedly." },
      { status: 500 },
    );
  }
}
