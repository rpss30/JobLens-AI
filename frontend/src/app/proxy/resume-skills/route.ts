import { NextResponse } from "next/server";

import { ApiError } from "@/lib/api/client";
import { extractResumeSkills } from "@/lib/api/endpoints";

/**
 * Thin proxy so the analyze form can pull skills out of a pasted resume before
 * the whole request is ready. The text is forwarded unchanged and never stored
 * here; FastAPI owns the extraction.
 */
export async function POST(request: Request) {
  let body: { resume_text?: unknown };

  try {
    body = (await request.json()) as { resume_text?: unknown };
  } catch {
    return NextResponse.json(
      { detail: "Request body must be valid JSON." },
      { status: 400 },
    );
  }

  if (typeof body.resume_text !== "string") {
    return NextResponse.json(
      { detail: "Provide resume text to read skills from." },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await extractResumeSkills(body.resume_text));
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Could not read skills from that resume." },
      { status: 500 },
    );
  }
}
