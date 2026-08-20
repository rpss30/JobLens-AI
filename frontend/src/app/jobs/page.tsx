import Link from "next/link";
import { Suspense } from "react";

import { BookmarkButton } from "@/components/domain/BookmarkButton";
import { CompanyLogo } from "@/components/domain/CompanyLogo";
import { JobDescription } from "@/components/domain/JobDescription";
import { JobFilters } from "@/components/domain/JobFilters";
import { JobSortMenu } from "@/components/domain/JobSortMenu";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
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

const SORT_OPTIONS = [
  { value: "search_relevance", label: "Relevance" },
  { value: "date_posted", label: "Date posted" },
  { value: "title", label: "Title" },
  { value: "company", label: "Company" },
  { value: "location", label: "Location" },
];

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
  filters?: string,
  savedOnly?: boolean,
): string {
  const params = new URLSearchParams({ dataset: datasetName, ...values });

  if (offset > 0) {
    params.set("offset", String(offset));
  }

  if (jobId) {
    params.set("job", jobId);
  }

  if (filters) {
    params.set("filters", filters);
  }

  if (savedOnly) {
    params.set("saved", "1");
  }

  return `/jobs?${params.toString()}`;
}

/**
 * The page numbers worth drawing: both ends, and a step either side of the
 * page being read. A run of six is more than a narrow column can spell out,
 * so the rest collapses to a gap.
 */
function pageWindow(current: number, total: number): (number | "gap")[] {
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

function BookmarkIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 20 20"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5.25 3.75h9.5v13l-4.75-3.25-4.75 3.25v-13Z" />
    </svg>
  );
}

function SlidersIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M4 7h10M18 7h2M4 12h4M12 12h8M4 17h10M18 17h2" />
      <circle cx="16" cy="7" r="1.9" />
      <circle cx="10" cy="12" r="1.9" />
      <circle cx="16" cy="17" r="1.9" />
    </svg>
  );
}

function BackIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M16 10H4M9 5l-5 5 5 5" />
    </svg>
  );
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
    <div className="flex min-h-0 flex-col gap-4 lg:h-full lg:rounded-xl lg:border lg:border-border lg:bg-surface lg:shadow-[0_1px_2px_rgba(16,21,31,0.04)]">
      {/* Outside the scrolling part, so which posting is open stays readable
          however far down the description you are. */}
      <div className="shrink-0 space-y-4 border-b border-border pb-4 pt-1 lg:px-6 lg:pt-6">
        {/* The buttons drop to their own row rather than squeezing the title
            into a column a few words wide. */}
        <div className="flex flex-wrap items-start gap-3">
          <CompanyLogo name={job.company} domain={job.company_domain} />

          <div className="min-w-[12rem] flex-1">
            <h2 className="text-xl font-medium text-text">{job.title}</h2>
            <p className="mt-0.5 flex items-center gap-1.5 text-sm text-text-muted">
              <BuildingIcon />
              <span className="truncate">{job.company}</span>
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
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
      </div>

      {/* Only a scroller once there is a height to scroll in: overscroll-contain
          swallows a touch even with nothing to scroll, which below lg left the
          page stuck unless the drag started outside the description. */}
      <div className="min-h-0 pb-1 lg:flex-1 lg:overflow-y-auto lg:overscroll-contain lg:px-6 lg:pb-6">
        <h3 className="text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle">
          About the job
        </h3>
        <div className="mt-2">
          <JobDescription
            description={job.description}
            formatted={job.description_formatted}
          />
        </div>
      </div>
    </div>
  );
}

function JobResultsSkeleton() {
  return (
    <>
      <Skeleton className="h-5 w-56 lg:shrink-0" />
      <div className="grid gap-5 lg:min-h-0 lg:flex-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
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
  filtersOpen,
  savedOnly,
}: {
  datasetName: string;
  values: JobFilterValues;
  offset: number;
  requestedJobId: string;
  filtersOpen: boolean;
  savedOnly: boolean;
}) {
  // Carried by every link on the page: opening a posting or turning a page is
  // not a reason for the panel someone just opened to shut itself.
  const filtersParam = filtersOpen ? "open" : "";
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
    savedOnly,
  });

  if (jobList.jobs.length === 0) {
    return savedOnly ? (
      <EmptyState
        title="Nothing saved yet"
        description="Open a posting and use the bookmark beside Apply to keep it here."
      />
    ) : (
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
  const pageCount = Math.max(1, Math.ceil(jobList.total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    /*
     * The pair takes whatever height the page has left and each column
     * scrolls inside its own box, so a long list never runs past the bottom
     * of the posting beside it. overscroll-contain stops a column that has
     * reached either end from handing the remaining scroll to the page.
     */
    <div className="grid gap-5 lg:min-h-0 lg:flex-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
      <Card
        // Narrow screens show one at a time: the list, or the posting it
        // opened. Both columns are side by side once there is room.
        className={`flex min-h-0 flex-col lg:h-full ${
          requestedJobId ? "hidden lg:flex" : ""
        }`}
      >
        <p
          className="shrink-0 border-b border-border px-4 py-3 text-sm text-text-muted"
          aria-live="polite"
        >
          Showing {formatCount(shownFrom)}–{formatCount(shownTo)} of{" "}
          {formatCount(jobList.total)}{" "}
          {savedOnly ? <span className="font-medium text-text">saved</span> : null}
          {savedOnly ? " " : ""}jobs
        </p>

        <ul className="divide-y divide-border lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:overscroll-contain">
          {jobList.jobs.map((job, index) => (
            <JobRow
              key={job.job_id || `${job.title}-${job.company}-${index}`}
              job={job}
              href={buildJobsHref(
                datasetName,
                values,
                offset,
                job.job_id,
                filtersParam,
                savedOnly,
              )}
              isSelected={job.job_id === selectedJob.job_id}
            />
          ))}
        </ul>

        {hasPrevious || hasNext ? (
          <nav
            aria-label="Job list pages"
            className="flex shrink-0 items-center justify-between gap-2 border-t border-border px-4 py-3"
          >
            {hasPrevious ? (
              <Link
                href={buildJobsHref(
                  datasetName,
                  values,
                  Math.max(0, offset - PAGE_SIZE),
                  "",
                  filtersParam,
                  savedOnly,
                )}
                className="shrink-0 text-sm font-medium text-accent hover:underline"
              >
                Previous
              </Link>
            ) : (
              <span />
            )}

            {/* Where you are in the run, and a way straight to anywhere else
                in it: six pages is too many to reach a step at a time. */}
            <div className="flex items-center gap-1">
              {pageWindow(currentPage, pageCount).map((page, index) =>
                page === "gap" ? (
                  <span
                    key={`gap-${index}`}
                    aria-hidden="true"
                    className="px-1 text-sm text-text-subtle"
                  >
                    &hellip;
                  </span>
                ) : page === currentPage ? (
                  <span
                    key={page}
                    aria-current="page"
                    className="rounded-md bg-accent-fill px-2 py-1 text-sm font-medium text-on-accent"
                  >
                    {page}
                  </span>
                ) : (
                  <Link
                    key={page}
                    href={buildJobsHref(
                      datasetName,
                      values,
                      (page - 1) * PAGE_SIZE,
                      "",
                      filtersParam,
                      savedOnly,
                    )}
                    aria-label={`Page ${page}`}
                    className="rounded-md px-2 py-1 text-sm text-text-muted transition-colors hover:bg-surface-muted hover:text-text"
                  >
                    {page}
                  </Link>
                ),
              )}
            </div>

            {hasNext ? (
              <Link
                href={buildJobsHref(
                  datasetName,
                  values,
                  offset + PAGE_SIZE,
                  "",
                  filtersParam,
                  savedOnly,
                )}
                className="shrink-0 text-sm font-medium text-accent hover:underline"
              >
                Next
              </Link>
            ) : (
              <span />
            )}
          </nav>
        ) : null}
      </Card>

      <div
        // The grid row already carries the viewport height, so the posting
        // fills it rather than setting a height of its own.
        className={`min-w-0 lg:relative lg:h-full ${
          requestedJobId
            ? // Bleeds past the page padding so the posting sits on white
              // rather than the page's own ground.
              "-mx-5 -my-8 min-h-[calc(100dvh-4rem)] bg-surface px-5 py-6 sm:-mx-8 sm:px-8 lg:mx-0 lg:my-0 lg:min-h-0 lg:bg-transparent lg:p-0"
            : "hidden lg:block"
        }`}
      >
        {/* Rides under the shell's own bar, and bleeds to both edges so the
            description passes behind it rather than beside it. */}
        <Link
          href={buildJobsHref(
            datasetName,
            values,
            offset,
            "",
            filtersParam,
            savedOnly,
          )}
          className="sticky top-16 z-20 -mx-5 mb-3 flex items-center gap-2 bg-surface px-5 py-3 text-sm font-medium text-text-muted transition-colors hover:text-text sm:-mx-8 sm:px-8 lg:hidden"
        >
          <BackIcon />
          Back to postings
        </Link>

        <div className="lg:absolute lg:inset-0 lg:overflow-hidden">
          <Suspense key={selectedJob.job_id} fallback={<JobDetailSkeleton />}>
            <JobDetailPane jobId={selectedJob.job_id} datasetName={datasetName} />
          </Suspense>
        </div>
      </div>
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

  /*
   * The filter panel is always open once there is room for it. On a narrow
   * screen it hides behind the toggle, and the toggle is a link so the panel
   * needs no state of its own.
   */
  const filtersOpen = readParam(params.filters, "") === "open";
  const savedOnly = readParam(params.saved, "") === "1";
  const activeFilterCount = [
    values.q.trim(),
    values.location === "Any" ? "" : values.location,
    values.company === "Any" ? "" : values.company,
    values.level === "Any" ? "" : values.level,
  ].filter(Boolean).length;
  const filtersToggleHref = buildJobsHref(
    datasetName,
    values,
    offset,
    requestedJobId,
    filtersOpen ? "" : "open",
    savedOnly,
  );

  const savedToggleHref = buildJobsHref(
    datasetName,
    values,
    // Back to the first page: the two lists do not share a page count.
    0,
    requestedJobId,
    filtersOpen ? "open" : "",
    !savedOnly,
  );

  const savedToggle = (
    <Link
      href={savedToggleHref}
      aria-pressed={savedOnly}
      // Level with the sort control, and carrying the accent once the list it
      // switches to is the one being shown. The mark stands on its own until
      // there is room for the words beside it.
      className={`inline-flex size-[2.375rem] shrink-0 items-center justify-center gap-2 rounded-lg border text-sm transition-colors lg:h-auto lg:w-auto lg:px-3.5 lg:py-2 ${
        savedOnly
          ? "border-transparent bg-accent-fill text-on-accent hover:bg-accent-fill-hover"
          : "border-border bg-surface text-text hover:bg-surface-muted"
      }`}
    >
      <span className="hidden lg:inline">
        {savedOnly ? "Showing saved jobs" : "Show saved jobs"}
      </span>
      <BookmarkIcon filled={savedOnly} />
    </Link>
  );

  const filtersToggle = (
    <Link
      href={filtersToggleHref}
      aria-expanded={filtersOpen}
      aria-label={filtersOpen ? "Hide filters" : "Show filters"}
      // Square, and the same 2.375rem height as the sort control beside it.
      // Carries the accent while the panel is open, the way every other
      // control in this interface shows that it is the one doing something.
      className={`relative inline-flex size-[2.375rem] shrink-0 items-center justify-center rounded-lg border transition-colors ${
        filtersOpen
          ? "border-transparent bg-accent-fill text-on-accent hover:bg-accent-fill-hover"
          : "border-border bg-surface text-text hover:bg-surface-muted"
      }`}
    >
      <SlidersIcon />
      {/* Only worth counting while the panel is shut: open, the filters
          speak for themselves. */}
      {!filtersOpen && activeFilterCount > 0 ? (
        <span className="absolute -right-1.5 -top-1.5 min-w-[1.125rem] rounded-full bg-accent-fill px-1 text-center text-[0.6875rem] font-medium leading-[1.125rem] text-on-accent">
          {activeFilterCount}
        </span>
      ) : null}
    </Link>
  );

  const sortMenu = (
    <JobSortMenu
      value={values.sort}
      options={SORT_OPTIONS.map((option) => ({
        ...option,
        // Changing the order keeps every other filter, and starts again from
        // the first page of results.
        href: buildJobsHref(
          datasetName,
          { ...values, sort: option.value },
          0,
          requestedJobId,
          filtersOpen ? "open" : "",
          savedOnly,
        ),
      }))}
    />
  );

  return (
    /*
     * From lg up the page is exactly as tall as the viewport and does not
     * scroll: the heading and filters take what they need and the results
     * take the rest. Anything that hangs below the fold is unreachable once
     * the columns stop passing their scroll on to the page.
     */
    <div className="space-y-8 lg:flex lg:h-[calc(100dvh-5rem)] lg:flex-col">
      {/*
       * Not PageHeader: the toggle has to sit level with the heading on a
       * narrow screen, and that component wraps its action below the
       * description instead.
       */}
      <header
        className={`items-start justify-between gap-4 lg:shrink-0 ${
          // A posting opened on a narrow screen is a page of its own.
          requestedJobId ? "hidden lg:flex" : "flex"
        }`}
      >
        <div className="min-w-0">
          <h1 className="text-3xl font-medium tracking-tight text-text sm:text-4xl">
            Jobs
          </h1>
          <p className="mt-2 max-w-2xl text-base text-text-muted">
            Every job in the selected dataset. Search and filter to narrow the
            list.
          </p>
        </div>

        <div className="hidden shrink-0 items-center gap-3 self-end lg:flex">
          <Badge tone="neutral">
            {formatDatasetLabel(filterOptions.dataset_name)}
          </Badge>
          {savedToggle}
          {sortMenu}
          {filtersToggle}
        </div>
      </header>

      {/* Below the description on a narrow screen, beside the heading above. */}
      <div
        className={`items-center justify-between gap-3 lg:hidden ${
          requestedJobId ? "hidden" : "flex"
        }`}
      >
        <div className="flex min-w-0 items-center gap-2">
          {sortMenu}
          {savedToggle}
        </div>
        {filtersToggle}
      </div>

      <div
        // Closed on arrival so the list gets the height instead. A posting
        // opened on a narrow screen is still a page of its own.
        className={`shrink-0 ${
          filtersOpen ? (requestedJobId ? "hidden lg:block" : "block") : "hidden"
        }`}
      >
        <JobFilters
          filterOptions={filterOptions}
          values={values}
          datasetName={datasetName}
        />
      </div>

      <Suspense
        // The opened posting is deliberately not part of this key. Including
        // it threw the whole results area back to a skeleton on every click,
        // list and all, when only the panel beside it was changing.
        key={`${values.q}|${values.location}|${values.company}|${values.level}|${values.sort}|${values.order}|${offset}|${savedOnly}`}
        fallback={<JobResultsSkeleton />}
      >
        <JobResults
          datasetName={datasetName}
          values={values}
          offset={offset}
          requestedJobId={requestedJobId}
          filtersOpen={filtersOpen}
          savedOnly={savedOnly}
        />
      </Suspense>
    </div>
  );
}
