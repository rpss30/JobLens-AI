"use server";

import { refresh } from "next/cache";

import { ApiError } from "@/lib/api/client";
import { deleteAnalysisRun, renameAnalysisRun } from "@/lib/api/endpoints";

export interface HistoryActionResult {
  ok: boolean;
  message: string;
}

function toResult(error: unknown, fallback: string): HistoryActionResult {
  return {
    ok: false,
    message: error instanceof ApiError ? error.message : fallback,
  };
}

export async function renameAnalysisRunAction(
  analysisRunId: number,
  newName: string,
): Promise<HistoryActionResult> {
  try {
    const result = await renameAnalysisRun(analysisRunId, newName);

    // refresh() re-renders the server-rendered list with the new name.
    refresh();

    return { ok: true, message: `Renamed to ${result.name}.` };
  } catch (error) {
    return toResult(error, "This saved result could not be renamed.");
  }
}

export async function deleteAnalysisRunAction(
  analysisRunId: number,
  name: string,
): Promise<HistoryActionResult> {
  try {
    await deleteAnalysisRun(analysisRunId);

    refresh();

    return { ok: true, message: `Deleted ${name}.` };
  } catch (error) {
    return toResult(error, "This saved result could not be deleted.");
  }
}
