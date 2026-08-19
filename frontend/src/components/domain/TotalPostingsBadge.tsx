import { getFilterOptions } from "@/lib/api/endpoints";
import { formatCount } from "@/lib/format";

/**
 * The posting count every Market Insights view carries beside its heading.
 *
 * It reads filter options rather than market insights because that call is a
 * cacheable GET returning the same total, so putting the badge in the page
 * header costs no second analysis request.
 */
export async function TotalPostingsBadge({
  datasetName,
}: {
  datasetName: string;
}) {
  const filterOptions = await getFilterOptions(datasetName);

  return (
    <span className="inline-flex items-baseline gap-1.5 rounded-full border border-border bg-surface-muted px-3.5 py-1.5 text-sm text-text-muted">
      <strong className="text-base font-semibold text-text">
        {formatCount(filterOptions.summary.job_count)}
      </strong>
      total postings
    </span>
  );
}

/** Holds the badge's space so the heading row does not jump when it lands. */
export function TotalPostingsBadgeSkeleton() {
  return (
    <span
      className="block h-9 w-36 rounded-full border border-border bg-surface-muted"
      aria-hidden="true"
    />
  );
}
