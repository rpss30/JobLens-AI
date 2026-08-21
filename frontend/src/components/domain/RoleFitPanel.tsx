import Link from "next/link";

import { CategoryIcon } from "@/components/charts/CategoryIcons";
import { Card } from "@/components/ui/Card";
import type { RoleScore } from "@/lib/api/types";
import { formatCount, formatPercent } from "@/lib/format";

/** As many as the chart can label without the rows closing up. */
const MAX_ROLES = 6;

const AXIS_TICKS = [0, 25, 50, 75, 100];

/*
 * The column template, shared by the axis and every row so the two line up.
 * Sized rather than auto on purpose: the axis row has only one cell in it, so
 * content-sized columns would collapse there and resolve to different widths
 * than the rows below, leaving the ticks a few pixels off their gridlines.
 *
 * Below md the row reflows to two columns and each cell is placed by hand,
 * which is why the order here is not the order in the markup.
 */
const CHART_COLUMNS =
  "md:grid-cols-[minmax(7rem,1.15fr)_5rem_minmax(0,2.6fr)_9.5rem]";

/*
 * Three steps of trust, from the matching engine's four labels. Nothing is
 * gated behind the colour: each pill says which step it is.
 */
const CONFIDENCE_STYLES: Record<string, string> = {
  High: "border-fit-met bg-fit-met-soft text-fit-met",
  Medium: "border-fit-stretch bg-fit-stretch-soft text-fit-stretch",
  Low: "border-confidence-low bg-confidence-low-soft text-confidence-low",
};

// Labels come from get_sample_confidence in the matching engine.
const CONFIDENCE_STEPS: Record<string, string> = {
  Strong: "High",
  Moderate: "Medium",
  Limited: "Low",
  Insufficient: "Low",
};

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  const step = CONFIDENCE_STEPS[confidence] ?? "Low";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium whitespace-nowrap ${CONFIDENCE_STYLES[step]}`}
    >
      {step} confidence
    </span>
  );
}

/** The lines a value is read against, drawn behind every row so they join up. */
function Gridlines() {
  return (
    <>
      {AXIS_TICKS.map((tick) => (
        <span
          key={tick}
          aria-hidden="true"
          style={{ left: `${tick}%` }}
          // The origin is solid: it is where every row starts, not a step
          // along the way.
          className={`absolute inset-y-0 w-px border-l border-border-strong ${
            tick === 0 ? "" : "border-dashed"
          }`}
        />
      ))}
    </>
  );
}

export function RoleFitPanel({
  roleScores,
  datasetName,
}: {
  roleScores: RoleScore[];
  datasetName: string;
}) {
  const rankedRoles = [...roleScores]
    .sort(
      (first, second) =>
        second.weighted_match_score - first.weighted_match_score,
    )
    .slice(0, MAX_ROLES);

  return (
    <Card className="px-5 py-5 sm:px-6 sm:py-6">
      {/* One grid so the link can sit beside the description from md and at
        the foot of the card below it, without being written out twice. */}
      <div className="grid gap-x-6 gap-y-5 md:grid-cols-[minmax(0,1fr)_auto]">
        <p className="text-sm text-text-muted md:col-start-1 md:row-start-1">
          See how well your current skills align with each role category in this
          dataset
        </p>

        {rankedRoles.length === 0 ? (
          <p className="py-6 text-sm text-text-muted">
            No role scores were produced for this search.
          </p>
        ) : (
          <div className="md:col-span-2 md:row-start-2">
            <div className="md:min-w-0">
              {/* Only from md: below it each row carries its own full-width
                track, and one shared axis would label none of them. */}
              <div
                aria-hidden="true"
                className={`hidden gap-x-4 md:grid ${CHART_COLUMNS}`}
              >
                <div className="relative h-6 md:col-start-3 md:-translate-x-10">
                  {AXIS_TICKS.map((tick) => (
                    <span
                      key={tick}
                      style={{ left: `${tick}%` }}
                      className="absolute -translate-x-1/2 text-xs text-text-subtle"
                    >
                      {tick} %
                    </span>
                  ))}
                </div>
              </div>

              <ul>
                {rankedRoles.map((role, index) => {
                  const position = Math.max(
                    0,
                    Math.min(100, role.weighted_match_score),
                  );
                  // Past this the label would hang off the end of the track.
                  const isNearEnd = position > 80;

                  return (
                    <li
                      key={role.role_category}
                      className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 py-3 md:gap-y-0 md:py-0 ${CHART_COLUMNS}`}
                    >
                      <span className="flex min-w-0 items-center gap-2 text-sm text-text md:col-start-1 md:row-start-1 md:translate-x-3">
                        {/* The same mark Market Insights gives this category,
                            so a role is recognised the same way everywhere. */}
                        <span className="shrink-0 text-text-muted">
                          <CategoryIcon category={role.role_category} />
                        </span>
                        <span className="truncate">{role.role_category}</span>
                      </span>

                      <span className="text-right text-sm tabular-nums text-text-muted md:hidden">
                        {formatPercent(role.weighted_match_score)}
                      </span>

                      <div className="col-span-2 md:col-span-1 md:col-start-3 md:row-start-1 md:-translate-x-10">
                        {/* A bar rather than a dot below md: a dot needs an axis
                        to be read against, and there is no width for one. */}
                        <div
                          className="h-2 overflow-hidden rounded-full bg-surface-muted md:hidden"
                          role="meter"
                          aria-valuenow={Math.round(role.weighted_match_score)}
                          aria-valuemin={0}
                          aria-valuemax={100}
                          aria-label={`${role.role_category} skill match`}
                        >
                          <div
                            className="h-full rounded-full bg-chart-mark"
                            style={{ width: `${position}%` }}
                          />
                        </div>

                        {/* Full row height so the gridlines in one row meet the
                        ones above and below without a seam. */}
                        <div className="relative hidden h-11 md:block">
                          <Gridlines />
                          <span
                            aria-hidden="true"
                            className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-border-strong"
                          />
                          <span
                            tabIndex={0}
                            style={{
                              left: `${position}%`,
                              // Staggered down the chart, so the dots read as one
                              // sweep rather than six things arriving at once.
                              animationDelay: `${index * 70}ms`,
                            }}
                            className="animate-dot-in peer absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-chart-mark outline-none ring-chart-mark/35 motion-safe:transition-[box-shadow] hover:ring-4 focus-visible:ring-4"
                            role="meter"
                            aria-valuenow={Math.round(
                              role.weighted_match_score,
                            )}
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-label={`${role.role_category} skill match`}
                          />

                          {/* The figure the column used to hold, now on the mark
                            it belongs to. Flipped to the near side past 80%,
                            where the far side runs out of track. */}
                          <span
                            aria-hidden="true"
                            style={{ left: `${position}%` }}
                            className={`pointer-events-none absolute top-1/2 -translate-y-1/2 rounded-md border border-border bg-surface px-2 py-0.5 text-xs font-semibold tabular-nums text-text opacity-0 shadow-[0_4px_12px_rgba(16,21,31,0.12)] transition-opacity peer-hover:opacity-100 peer-focus-visible:opacity-100 ${
                              isNearEnd ? "-translate-x-full -ml-3" : "ml-3"
                            }`}
                          >
                            {formatPercent(role.weighted_match_score)}
                          </span>
                        </div>
                      </div>

                      <span className="text-sm tabular-nums text-text-muted md:col-start-2 md:row-start-1 md:-translate-x-10 md:text-right">
                        {formatCount(role.sample_size)}{" "}
                        {role.sample_size === 1 ? "job" : "jobs"}
                      </span>

                      <div className="text-right md:col-start-4 md:row-start-1 md:justify-self-end">
                        <ConfidenceBadge confidence={role.sample_confidence} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        )}

        <Link
          href={`/skills/role-distribution?dataset=${encodeURIComponent(datasetName)}`}
          // The page this leads to arrives behind a Suspense boundary, so it
          // commits before there is content to scroll and the reader lands
          // part way down a page they have not seen the top of.
          onClick={() => window.scrollTo({ top: 0 })}
          className="inline-flex items-center gap-2 text-sm font-medium text-accent hover:underline md:col-start-2 md:row-start-1 md:justify-self-end"
        >
          View all roles
          <span aria-hidden="true">&rarr;</span>
        </Link>
      </div>
    </Card>
  );
}
