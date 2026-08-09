"use server";

import { refresh } from "next/cache";

import { ApiError } from "@/lib/api/client";
import {
  deleteDataset,
  renameDataset,
  uploadDataset,
} from "@/lib/api/endpoints";

export interface DatasetActionResult {
  ok: boolean;
  message: string;
}

function toResult(error: unknown, fallback: string): DatasetActionResult {
  return {
    ok: false,
    message: error instanceof ApiError ? error.message : fallback,
  };
}

export async function uploadDatasetAction(
  formData: FormData,
): Promise<DatasetActionResult> {
  try {
    const result = await uploadDataset(formData);

    // refresh() re-renders the server component list with the new dataset.
    refresh();

    return {
      ok: true,
      message: `Saved ${result.dataset_name} with ${result.job_count} postings.`,
    };
  } catch (error) {
    return toResult(error, "The dataset could not be uploaded.");
  }
}

export async function renameDatasetAction(
  datasetName: string,
  newName: string,
): Promise<DatasetActionResult> {
  try {
    const result = await renameDataset(datasetName, newName);

    refresh();

    return { ok: true, message: `Renamed to ${result.new_name}.` };
  } catch (error) {
    return toResult(error, "The dataset could not be renamed.");
  }
}

export async function deleteDatasetAction(
  datasetName: string,
): Promise<DatasetActionResult> {
  try {
    await deleteDataset(datasetName);

    refresh();

    return { ok: true, message: `Deleted ${datasetName}.` };
  } catch (error) {
    return toResult(error, "The dataset could not be deleted.");
  }
}
