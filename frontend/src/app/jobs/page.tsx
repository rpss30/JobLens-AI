import Link from "next/link";
import { Suspense } from "react";

import { JobFilters } from "@/components/domain/JobFilters";
import { JobListingCard } from "@/components/domain/JobListingCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { CardSkeleton, EmptyState, Skeleton } from "@/components/ui/States";
import { getFilterOptions, getJobs } from "@/lib/api/endpoints";
import type { SearchMode } from "@/lib/api/types";
import { resolveDataset } from "@/lib/datasets";
import { formatCount, formatDatasetLabel } from "@/lib/format";

const PAGE_SIZE = 12;

function readParam(
  value: string | string[] | undefined,
  fallback: string,
): string {
  if (Array.isArray(value)) {
    return value[0] ?? fallback;
  }

  return value ?? fallback;
}

function buildPageHref(
  datasetName: string,
  values: JobFilterValues,
  offset: number,
): string {
  const params = new URLSearchParams({ dataset: datasetName, ...values });

  if (offset > 0) {
    params.set("offset", String(offset));
  }

  return `/jobs?${params.toString()}`;
}

interface JobFilterValues {
  q: string;
  location: string;
  level: string;
  sort: string;
  order: string;
}

function JobResultsSkeleton() {
  return (
    <>
      <Skeleton className="h-5 w-56" />
      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <CardSkeleton key={index} rows={3} />
        ))}
      </div>
    </>
  );
}

/** Only this part re-suspends on a new search, so the filters stay usable. */
async function JobResults({
  datasetName,
  values,
  offset,
}: {
  datasetName: string;
  values: JobFilterValues;
  offset: number;
}) {
  const jobList = await getJobs({
    datasetName,
    searchQuery: values.q,
    searchMode: "tfidf" as SearchMode,
    location: values.location,
    experienceLevel: values.level,
    sortBy: values.sort,
    sortOrder: values.order === "asc" ? "asc" : "desc",
    limit: PAGE_SIZE,
    offset,
  });

  if (jobList.jobs.length === 0) {
    return (
      <EmptyState
        title="No jobs match these filters"
        description="Try a shorter search, a different location, or set the experience level back to any."
      />
    );
  }

  const shownFrom = offset + 1;
  const shownTo = Math.min(offset + PAGE_SIZE, jobList.total);
  const hasPrevious = offset > 0;
  const hasNext = shownTo < jobList.total;

  return (
    <>
      <p className="text-sm text-text-muted" aria-live="polite">
        Showing {formatCount(shownFrom)}–{formatCount(shownTo)} of{" "}
        {formatCount(jobList.total)} jobs
      </p>

      <div className="grid gap-4 xl:grid-cols-2">
        {jobList.jobs.map((job, index) => (
          <JobListingCard
            key={job.job_id || `${job.title}-${job.company}-${index}`}
            job={job}
          />
        ))}
      </div>

      {hasPrevious || hasNext ? (
        <nav
          aria-label="Job list pages"
          className="flex items-center justify-between border-t border-border pt-4"
        >
          {hasPrevious ? (
            <Link
              href={buildPageHref(
                datasetName,
                values,
                Math.max(0, offset - PAGE_SIZE),
              )}
              className="text-sm font-medium text-accent hover:underline"
            >
              Previous
            </Link>
          ) : (
            <span />
          )}

          {hasNext ? (
            <Link
              href={buildPageHref(datasetName, values, offset + PAGE_SIZE)}
              className="text-sm font-medium text-accent hover:underline"
            >
              Next
            </Link>
          ) : (
            <span />
          )}
        </nav>
      ) : null}
    </>
  );
}

export default async function JobsPage({ searchParams }: PageProps<"/jobs">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  const values: JobFilterValues = {
    q: readParam(params.q, ""),
    location: readParam(params.location, "Any"),
    level: readParam(params.level, "Any"),
    sort: readParam(params.sort, "search_relevance"),
    order: readParam(params.order, "desc"),
  };

  const offset = Math.max(0, Number(readParam(params.offset, "0")) || 0);
  const filterOptions = await getFilterOptions(datasetName);

  return (
    <>
      <PageHeader
        title="Jobs"
        description="Every job in the selected dataset. Search and filter to narrow the list."
        action={
          <Badge tone="neutral">
            {formatDatasetLabel(filterOptions.dataset_name)}
          </Badge>
        }
      />

      <JobFilters
        filterOptions={filterOptions}
        values={values}
        datasetName={datasetName}
      />

      <Suspense
        key={`${values.q}|${values.location}|${values.level}|${values.sort}|${values.order}|${offset}`}
        fallback={<JobResultsSkeleton />}
      >
        <JobResults
          datasetName={datasetName}
          values={values}
          offset={offset}
        />
      </Suspense>
    </>
  );
}
