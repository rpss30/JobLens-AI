import { NextResponse } from "next/server";

import { ApiError } from "@/lib/api/client";
import { unsaveJob } from "@/lib/api/endpoints";

/** Thin proxy for dropping a kept posting from the client. */
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;
  const datasetName = new URL(request.url).searchParams.get("dataset_name");

  if (!datasetName) {
    return NextResponse.json(
      { detail: "A dataset_name is required." },
      { status: 400 },
    );
  }

  try {
    return NextResponse.json(await unsaveJob(jobId, datasetName));
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Could not unsave this job." },
      { status: 500 },
    );
  }
}
