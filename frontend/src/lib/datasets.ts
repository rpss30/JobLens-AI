export const DEFAULT_DATASET = "canada_snapshot";

export const LOCAL_DATASETS = [
  {
    value: "canada_snapshot",
    label: "Canada snapshot",
    group: "Bundled datasets",
  },
  {
    value: "local_sample",
    label: "Local sample",
    group: "Bundled datasets",
  },
];

/**
 * Reads the active dataset from a page's search params, falling back to the
 * richest bundled dataset so first-time visitors see real postings.
 */
export function resolveDataset(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? DEFAULT_DATASET;
  }

  return value?.trim() || DEFAULT_DATASET;
}
