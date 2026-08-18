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

/**
 * Appends the active dataset to a link so a switched dataset survives
 * navigation. The sidebar links are bare paths, but the separator is chosen
 * rather than assumed so a href that already carries a query still works.
 */
export function withDataset(
  href: string,
  datasetName: string | null | undefined,
): string {
  if (!datasetName?.trim()) {
    return href;
  }

  const separator = href.includes("?") ? "&" : "?";

  return `${href}${separator}dataset=${encodeURIComponent(datasetName)}`;
}
