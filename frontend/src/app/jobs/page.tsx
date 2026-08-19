import Link from "next/link";
import { Suspense } from "react";

import { BookmarkButton } from "@/components/domain/BookmarkButton";
import { CompanyLogo } from "@/components/domain/CompanyLogo";
import { JobDescription } from "@/components/domain/JobDescription";
import { JobFilters } from "@/components/domain/JobFilters";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody } from "@/components/ui/Card";
import { CardSkeleton, EmptyState, Skeleton } from "@/components/ui/States";
import {
  getFilterOptions,
  getJob,
  getJobs,
  getSavedJobs,
} from "@/lib/api/endpoints";
import type { JobListing, SearchMode } from "@/lib/api/types";
import { resolveDataset } from "@/lib/datasets";
import { formatCount, formatDate, formatDatasetLabel } from "@/lib/format";

const PAGE_SIZE = 12;

interface JobFilterValues {
  q: string;
  location: string;
  company: string;
  level: string;
  sort: string;
  order: string;
}

function readParam(
  value: string | string[] | undefined,
  fallback: string,
): string {
  if (Array.isArray(value)) {
    return value[0] ?? fallback;
  }

  return value ?? fallback;
}

/** A link back to this list, optionally opening one posting or another page. */
function buildJobsHref(
  datasetName: string,
  values: JobFilterValues,
  offset: number,
  jobId?: string,
): string {
  const params = new URLSearchParams({ dataset: datasetName, ...values });

  if (offset > 0) {
    params.set("offset", String(offset));
  }

  if (jobId) {
    params.set("job", jobId);
  }

  return `/jobs?${params.toString()}`;
}

function PinIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M16 8.5c0 4-6 9-6 9s-6-5-6-9a6 6 0 0 1 12 0Z" />
      <circle cx="10" cy="8.25" r="2" />
    </svg>
  );
}

function BuildingIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M4.75 16.75V4.5a.75.75 0 0 1 .75-.75h6.5a.75.75 0 0 1 .75.75v12.25M12.75 9.25h2.5v7.5M3.5 16.75h13" />
      <path d="M7.25 7h2M7.25 10h2M7.25 13h2" />
    </svg>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-muted px-2.5 py-1 text-xs text-text-muted">
      {children}
    </span>
  );
}

function JobRow({
  job,
  href,
  isSelected,
}: {
  job: JobListing;
  href: string;
  isSelected: boolean;
}) {
  return (
    <li>
      <Link
        href={href}
        aria-current={isSelected ? "true" : undefined}
        // The bar carries the selection as well as the tint, so it does not
        // rest on colour alone.
        className={`flex gap-3 border-l-2 px-4 py-3 transition-colors ${
          isSelected
            ? "border-accent bg-accent-soft"
            : "border-transparent hover:bg-surface-muted"
        }`}
      >
        <CompanyLogo name={job.company} domain={job.company_domain} />

        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-text">
            {job.title}
          </span>
          <span className="block truncate text-sm text-text-muted">
            {job.company}
          </span>
          <span className="mt-1 flex items-center gap-1 text-xs text-text-muted">
            <PinIcon />
            <span className="truncate">{job.location}</span>
          </span>
          {job.date_posted ? (
            <span className="mt-0.5 block text-xs text-text-subtle">
              {formatDate(job.date_posted)}
            </span>
          ) : null}
        </span>
      </Link>
    </li>
  );
}

function JobDetailSkeleton() {
  return <CardSkeleton rows={8} />;
}

async function JobDetailPane({
  jobId,
  datasetName,
}: {
  jobId: string;
  datasetName: string;
}) {
  const job = await getJob(jobId, datasetName);

  // Saved jobs need PostgreSQL. Browsing should not stop when it is down, so
  // an unreachable list only means nothing is known to be saved.
  let isSaved = false;

  try {
    const saved = await getSavedJobs(datasetName);
    isSaved = saved.some((entry) => entry.job_id === job.job_id);
  } catch {
    isSaved = false;
  }

  return (
    <Card className="flex min-h-0 flex-col lg:h-full">
      <CardBody className="min-h-0 space-y-4 overflow-y-auto p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <CompanyLogo name={job.company} domain={job.company_domain} />

          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-medium text-text">{job.title}</h2>
            <p className="mt-0.5 flex items-center gap-1.5 text-sm text-text-muted">
              <BuildingIcon />
              <span className="truncate">{job.company}</span>
            </p>
          </div>

          <BookmarkButton
            job={job}
            datasetName={datasetName}
            initiallySaved={isSaved}
          />

          {job.source_url ? (
            <a
              href={job.source_url}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-accent-fill px-4 py-2.5 text-sm font-medium text-on-accent transition-opacity hover:opacity-90"
            >
              Apply
              <span aria-hidden="true">↗</span>
            </a>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          {job.location ? (
            <Pill>
              <PinIcon />
              {job.location}
            </Pill>
          ) : null}
          {job.date_posted ? (
            <Pill>Posted {formatDate(job.date_posted)}</Pill>
          ) : null}
          {job.employment_type ? <Pill>{job.employment_type}</Pill> : null}
          {job.experience_level ? <Pill>{job.experience_level}</Pill> : null}
        </div>

        <div className="border-t border-border pt-4">
          <h3 className="text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle">
            About the job
          </h3>
          <div className="mt-2">
            <JobDescription description={job.description} />
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function JobResultsSkeleton() {
  return (
    <>
      <Skeleton className="h-5 w-56" />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <CardSkeleton rows={6} />
        <CardSkeleton rows={8} />
      </div>
    </>
  );
}

/** Only this part re-suspends on a new search, so the filters stay usable. */
async function JobResults({
  datasetName,
  values,
  offset,
  requestedJobId,
}: {
  datasetName: string;
  values: JobFilterValues;
  offset: number;
  requestedJobId: string;
}) {
  const jobList = await getJobs({
    datasetName,
    searchQuery: values.q,
    searchMode: "tfidf" as SearchMode,
    location: values.location,
    experienceLevel: values.level,
    company: values.company,
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

  // A posting from a previous filter will not be on this page, so the list
  // falls back to opening its first row rather than an empty panel.
  const selectedJob =
    jobList.jobs.find((job) => job.job_id === requestedJobId) ?? jobList.jobs[0];

  const shownFrom = offset + 1;
  const shownTo = Math.min(offset + PAGE_SIZE, jobList.total);
  const hasPrevious = offset > 0;
  const hasNext = shownTo < jobList.total;

  return (
    /*
     * Both columns share the row's height from lg up and scroll inside it, so
     * the description ends level with the list rather than running past the
     * bottom of it.
     */
    <div className="grid gap-5 lg:h-[calc(100vh-17rem)] lg:min-h-[34rem] lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <Card className="flex min-h-0 flex-col lg:h-full">
        <p
          className="border-b border-border px-4 py-3 text-sm text-text-muted"
          aria-live="polite"
        >
          Showing {formatCount(shownFrom)}–{formatCount(shownTo)} of{" "}
          {formatCount(jobList.total)} jobs
        </p>

        <ul className="min-h-0 flex-1 divide-y divide-border overflow-y-auto">
          {jobList.jobs.map((job, index) => (
            <JobRow
              key={job.job_id || `${job.title}-${job.company}-${index}`}
              job={job}
              href={buildJobsHref(datasetName, values, offset, job.job_id)}
              isSelected={job.job_id === selectedJob.job_id}
            />
          ))}
        </ul>

        {hasPrevious || hasNext ? (
          <nav
            aria-label="Job list pages"
            className="flex items-center justify-between border-t border-border px-4 py-3"
          >
            {hasPrevious ? (
              <Link
                href={buildJobsHref(
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
                href={buildJobsHref(datasetName, values, offset + PAGE_SIZE)}
                className="text-sm font-medium text-accent hover:underline"
              >
                Next
              </Link>
            ) : (
              <span />
            )}
          </nav>
        ) : null}
      </Card>

      <Suspense key={selectedJob.job_id} fallback={<JobDetailSkeleton />}>
        <JobDetailPane jobId={selectedJob.job_id} datasetName={datasetName} />
      </Suspense>
    </div>
  );
}

export default async function JobsPage({ searchParams }: PageProps<"/jobs">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  const values: JobFilterValues = {
    q: readParam(params.q, ""),
    location: readParam(params.location, "Any"),
    company: readParam(params.company, "Any"),
    level: readParam(params.level, "Any"),
    sort: readParam(params.sort, "search_relevance"),
    order: readParam(params.order, "desc"),
  };

  const requestedJobId = readParam(params.job, "");
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
        key={`${values.q}|${values.location}|${values.company}|${values.level}|${values.sort}|${values.order}|${offset}|${requestedJobId}`}
        fallback={<JobResultsSkeleton />}
      >
        <JobResults
          datasetName={datasetName}
          values={values}
          offset={offset}
          requestedJobId={requestedJobId}
        />
      </Suspense>
    </>
  );
}
