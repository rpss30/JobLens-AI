import Link from "next/link";
import { Suspense } from "react";

import { LocationMap, type MapPin } from "@/components/charts/LocationMap";
import { WorkplaceRadials } from "@/components/charts/WorkplaceRadials";
import {
  TotalPostingsBadge,
  TotalPostingsBadgeSkeleton,
} from "@/components/domain/TotalPostingsBadge";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { CardSkeleton } from "@/components/ui/States";
import { getMarketInsights } from "@/lib/api/endpoints";
import type { LocationDemand } from "@/lib/api/types";
import { resolveDataset, withDataset } from "@/lib/datasets";
import { formatCount } from "@/lib/format";
import { coordinatesFor } from "@/lib/geo/cities";

function MapIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M1.75 4.5 6.25 2.5v11L1.75 15.5v-11Z" />
      <path d="M6.25 2.5l5.5 2v11l-5.5-2v-11Z" />
      <path d="M11.75 4.5 16.25 2.5v11l-4.5 2v-11Z" />
    </svg>
  );
}

function ListIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M6.5 4.5h9M6.5 9h9M6.5 13.5h9M2.5 4.5h.01M2.5 9h.01M2.5 13.5h.01" />
    </svg>
  );
}

function LaptopIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0 text-accent"
    >
      <path d="M4.25 4.75h11.5v8H4.25v-8Z" />
      <path d="M2.25 15.25h15.5" />
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0 text-accent"
    >
      <circle cx="10" cy="10" r="7.25" />
      <path d="M2.75 10h14.5M10 2.75c1.9 2 2.9 4.5 2.9 7.25S11.9 15.25 10 17.25C8.1 15.25 7.1 12.75 7.1 10S8.1 4.75 10 2.75Z" />
    </svg>
  );
}

function FlagIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0 text-accent"
    >
      <path d="M4.75 17.25V3.5M4.75 4.25h9.5l-1.75 3 1.75 3h-9.5" />
    </svg>
  );
}

function PinOffIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0 text-accent"
    >
      <path d="M15 8.5c0 3.5-5 8.75-5 8.75S5 12 5 8.5a5 5 0 0 1 7.6-4.28" />
      <path d="M3 3l14 14" />
    </svg>
  );
}

/**
 * Where a place's postings live on the Jobs page.
 *
 * The label is sent as it is counted here, because the Jobs filter resolves
 * it through the same normalization. That is what makes the list on the
 * other end exactly the postings behind the number beside it.
 */
function jobsHref(row: LocationDemand, datasetName: string): string {
  return withDataset(
    `/jobs?location=${encodeURIComponent(row.location)}&filters=open`,
    datasetName,
  );
}

/** A place the map cannot pin, and why it cannot. */
function unplaceableIcon(row: LocationDemand) {
  if (row.remote) {
    return <LaptopIcon />;
  }

  if (!row.city && row.region) {
    return <FlagIcon />;
  }

  if (!row.city) {
    return <GlobeIcon />;
  }

  return <PinOffIcon />;
}

function LegendRow({
  icon,
  label,
  value,
  href,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  href?: string;
}) {
  const row = (
    <>
      {icon}
      <span className="min-w-0 flex-1 truncate text-xs text-text" title={label}>
        {label}
      </span>
      <span className="text-xs font-semibold tabular-nums text-text">
        {formatCount(value)}
      </span>
    </>
  );

  return (
    <li>
      {href ? (
        <Link
          href={href}
          className="-mx-1 flex items-center gap-2 rounded px-1 py-0.5 transition-colors hover:bg-surface-muted"
        >
          {row}
        </Link>
      ) : (
        <span className="flex items-center gap-2">{row}</span>
      )}
    </li>
  );
}

function RankRow({
  rank,
  label,
  value,
  share,
  href,
}: {
  rank: number;
  label: string;
  value: number;
  share: number;
  href: string;
}) {
  return (
    <li>
      <Link
        href={href}
        className="-mx-2 flex items-center gap-2 rounded-lg px-2 py-2 transition-colors hover:bg-surface-muted sm:gap-3"
      >
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-surface-muted text-xs tabular-nums text-text-subtle">
          {rank}
        </span>
        <span
          className="min-w-0 flex-1 truncate text-sm text-text sm:w-40 sm:flex-none"
          title={label}
        >
          {label}
        </span>
        {/* The count beside it already carries the comparison, so the bar is
            the first thing to go when there is no room for it. */}
        <span className="hidden h-2 min-w-0 rounded-full bg-surface-muted sm:block sm:flex-1">
          <span
            className="block h-2 rounded-full bg-chart-2"
            style={{ width: `${Math.max(share * 100, 2)}%` }}
          />
        </span>
        <span className="w-10 shrink-0 text-right text-sm tabular-nums text-text">
          {formatCount(value)}
        </span>
      </Link>
    </li>
  );
}

async function JobLocations({ datasetName }: { datasetName: string }) {
  // 25 is the API's ceiling, and enough for a map and a ranking.
  const insights = await getMarketInsights({ datasetName, topN: 25 });
  const locations = insights.jobs_by_location;

  const pins: MapPin[] = [];
  const unplaceable: LocationDemand[] = [];

  for (const row of locations) {
    const at = coordinatesFor(row.city, row.region, row.country);

    if (at) {
      pins.push({
        label: row.location,
        value: row.job_count,
        at,
        href: jobsHref(row, datasetName),
      });
    } else {
      unplaceable.push(row);
    }
  }

  // Only cities are ranked. A country-wide or province-wide row is not a
  // place you could take a job in, and "Canada" heading the list above
  // Toronto told the reader nothing. Those rows keep their counts in the
  // cards under the map instead.
  const ranked = locations.filter((row) => row.city);
  const topValue = ranked[0]?.job_count ?? 0;

  return (
    <Card>
      <CardBody className="space-y-5 p-5 sm:p-6">
        {/*
         * The map reads second from lg up and first when the columns stack.
         * Ordering rather than reordering the markup keeps the narrow layout
         * exactly as it was, with the map above the list it belongs to.
         */}
        <div className="grid gap-5 lg:grid-cols-[2fr_3fr]">
          <section className="flex h-full flex-col gap-4 rounded-xl border border-border p-4 lg:order-2">
            <h2 className="flex items-center gap-2 text-base font-medium text-text">
              <MapIcon />
              Map view
            </h2>

            <div className="relative min-h-64 flex-1">
              <LocationMap pins={pins} />

              {unplaceable.length > 0 ||
              insights.postings_without_location > 0 ? (
                <div className="absolute right-0 top-0 w-44 rounded-lg border border-border bg-surface/95 p-2.5">
                  <p className="mb-1.5 text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle">
                    Not tied to a city
                  </p>
                  <ul className="space-y-1">
                    {unplaceable.map((row) => (
                      <LegendRow
                        key={row.location}
                        icon={unplaceableIcon(row)}
                        label={row.location}
                        value={row.job_count}
                        href={jobsHref(row, datasetName)}
                      />
                    ))}
                    {insights.postings_without_location > 0 ? (
                      <LegendRow
                        icon={<PinOffIcon />}
                        label="No location given"
                        value={insights.postings_without_location}
                      />
                    ) : null}
                  </ul>
                </div>
              ) : null}
            </div>
          </section>

          <div className="flex flex-col gap-5 lg:order-1">
            <section className="rounded-xl border border-border p-4">
              <h2 className="flex items-center gap-2 text-base font-medium text-text">
                <ListIcon />
                Ranked locations
              </h2>

              <div className="mt-3 flex items-center gap-2 border-b border-border pb-2 text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle sm:gap-3 sm:text-xs">
                <span className="w-6 shrink-0">#</span>
                <span className="min-w-0 flex-1 sm:w-40 sm:flex-none">
                  Location
                </span>
                <span className="hidden min-w-0 sm:block sm:flex-1" />
                <span className="w-10 shrink-0 text-right">Jobs</span>
              </div>

              <ul className="divide-y divide-border">
                {ranked.map((row, index) => (
                  <RankRow
                    key={row.location}
                    rank={index + 1}
                    label={row.location}
                    value={row.job_count}
                    share={topValue > 0 ? row.job_count / topValue : 0}
                    href={jobsHref(row, datasetName)}
                  />
                ))}
              </ul>
            </section>

            <section className="flex flex-1 items-center rounded-xl border border-border p-4">
              <WorkplaceRadials
                data={insights.workplace_types}
                total={insights.jobs_analyzed}
              />
            </section>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

export default async function JobLocationsPage({
  searchParams,
}: PageProps<"/skills/locations">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Job Locations"
        description="Posting concentration by location."
        action={
          <Suspense fallback={<TotalPostingsBadgeSkeleton />}>
            <TotalPostingsBadge datasetName={datasetName} />
          </Suspense>
        }
      />

      <Suspense key={datasetName} fallback={<CardSkeleton rows={10} />}>
        <JobLocations datasetName={datasetName} />
      </Suspense>
    </>
  );
}
