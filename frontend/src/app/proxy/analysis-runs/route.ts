import { NextResponse } from "next/server";

import { ApiError } from "@/lib/api/client";
import { createAnalysisRun } from "@/lib/api/endpoints";
import type { CreateAnalysisRunRequest } from "@/lib/api/types";

/** Thin proxy for saving an analysis run from the client. */
export async function POST(request: Request) {
  let body: CreateAnalysisRunRequest;

  try {
    body = (await request.json()) as CreateAnalysisRunRequest;
  } catch {
    return NextResponse.json(
      { detail: "Request body must be valid JSON." },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await createAnalysisRun(body), { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Could not save this analysis run." },
      { status: 500 },
    );
  }
}
