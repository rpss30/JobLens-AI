import { NextResponse } from "next/server";

import { ApiError } from "@/lib/api/client";
import { getJob } from "@/lib/api/endpoints";

/**
 * Thin proxy for reading one posting from the client.
 *
 * The Jobs tab fetches a posting on the server, because which one is open
 * lives in its URL. A result is held in memory instead, so the matched job
 * being read is only ever known to the browser.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;
  const datasetName = new URL(request.url).searchParams.get("dataset_name");

  try {
    return NextResponse.json(await getJob(jobId, datasetName));
  } catch (error) {
    if (error instanceof ApiError) {
      return NextResponse.json(
        { detail: error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Could not load this posting." },
      { status: 500 },
    );
  }
}
