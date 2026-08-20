/**
 * The page numbers worth drawing: both ends, and a step either side of the
 * page being read. A run of six is more than a narrow column can spell out,
 * so the rest collapses to a gap.
 */
export function pageWindow(
  current: number,
  total: number,
): (number | "gap")[] {
  const wanted = [1, total, current - 1, current, current + 1];
  const shown = [...new Set(wanted)]
    .filter((page) => page >= 1 && page <= total)
    .sort((first, second) => first - second);

  return shown.flatMap((page, index) =>
    index > 0 && page - shown[index - 1] > 1
      ? (["gap", page] as (number | "gap")[])
      : [page],
  );
}
