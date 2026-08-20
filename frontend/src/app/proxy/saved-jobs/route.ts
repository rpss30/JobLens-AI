import { NextResponse } from "next/server";

import { ApiError } from "@/lib/api/client";
import { saveJob } from "@/lib/api/endpoints";
import type { SaveJobRequest } from "@/lib/api/types";

/** Thin proxy for keeping a posting from the client. */
export async function POST(request: Request) {
  let body: SaveJobRequest;

  try {
    body = (await request.json()) as SaveJobRequest;
  } catch {
    return NextResponse.json(
      { detail: "Request body must be valid JSON." },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await saveJob(body), { status: 201 });
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Could not save this job." },
      { status: 500 },
    );
  }
}
