"use client";

import { useState, type ReactNode } from "react";

import { CompanyLogo } from "@/components/domain/CompanyLogo";
import { MatchDetail } from "@/components/domain/MatchDetail";
import { ExperienceFitBadge } from "@/components/domain/MatchMarks";
import { Card } from "@/components/ui/Card";
import type { JobMatch } from "@/lib/api/types";
import { formatCount, formatDate } from "@/lib/format";
import { pageWindow } from "@/lib/pagination";

const PAGE_SIZE = 12;

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

function MatchRow({
  job,
  isSelected,
  onSelect,
}: {
  job: JobMatch;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-current={isSelected ? "true" : undefined}
        // The bar carries the selection as well as the tint, so it does not
        // rest on colour alone.
        className={`flex w-full gap-3 border-l-2 px-4 py-3 text-left transition-colors ${
          isSelected
            ? "border-accent bg-accent-soft"
            : "border-transparent hover:bg-surface-muted"
        }`}
      >
        <CompanyLogo name={job.company} domain={job.company_domain} />

        <span className="min-w-0 flex-1">
          <span className="flex items-start justify-between gap-2">
            <span className="min-w-0 truncate text-sm font-medium text-text">
              {job.title}
            </span>
            {/* The one number the reader is scanning this list for, so it
                sits in the row rather than only in the panel beside it. */}
            <span className="shrink-0 text-sm font-semibold tabular-nums text-text">
              {Math.round(job.skill_match_score)}%
            </span>
          </span>
          <span className="block truncate text-sm text-text-muted">
            {job.company}
          </span>
          <span className="mt-1 flex items-center gap-1 text-xs text-text-muted">
            <PinIcon />
            <span className="truncate">{job.location}</span>
          </span>
          {/* The badge leads: how far out of reach a job is is what the
              reader is scanning for, and most of this dataset never recorded
              a date to put in front of it. */}
          <span className="mt-1.5 flex flex-wrap items-center gap-2">
            <ExperienceFitBadge fit={job.experience_fit} />
            {job.date_posted ? (
              <span className="text-xs text-text-subtle">
                {formatDate(job.date_posted)}
              </span>
            ) : null}
          </span>
        </span>
      </button>
    </li>
  );
}

/**
 * The matched jobs, read the way the Jobs tab reads a dataset: filters at the
 * top of the card, the list down one side, and the posting open beside it.
 *
 * Which one is open is state rather than a URL, because the result behind it
 * is held in memory and a shared link would arrive at nothing.
 */
export function MatchResults({
  jobs,
  datasetName,
  savedJobIds,
  filtersPanel,
}: {
  /** Already narrowed and ordered by the section above. */
  jobs: JobMatch[];
  datasetName: string;
  savedJobIds: string[];
  /** Rendered as the top of the shared card, or nothing while it is shut. */
  filtersPanel: ReactNode;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  // Below lg the list and the posting are one page at a time, so opening one
  // is a move rather than a change to the panel beside it.
  const [isReadingOne, setIsReadingOne] = useState(false);

  const savedIds = new Set(savedJobIds);
  const pageCount = Math.max(1, Math.ceil(jobs.length / PAGE_SIZE));
  // A filter that shortens the list can strand the page being read past the
  // end of it, so the page is clamped rather than reset by an effect.
  const currentPage = Math.min(page, pageCount - 1);
  const offset = currentPage * PAGE_SIZE;
  const pageJobs = jobs.slice(offset, offset + PAGE_SIZE);

  // A match from a previous filter will not be on this page, so the list
  // falls back to opening its first row rather than an empty panel.
  const selected =
    pageJobs.find((job) => job.job_id === selectedId) ?? pageJobs[0];

  function openMatch(job: JobMatch) {
    setSelectedId(job.job_id);
    setIsReadingOne(true);
  }

  function turnTo(nextPage: number) {
    setPage(nextPage);
    setSelectedId(null);
  }

  return (
    /* From lg the filters and the results share one surface, so the panel
       reads as the top of the list rather than a card floating above it.
       Below lg they stay two cards with the section's own gap between. */
    <div className="space-y-6 lg:space-y-0 lg:overflow-hidden lg:rounded-xl lg:border lg:border-border lg:bg-surface lg:shadow-[0_1px_2px_rgba(16,21,31,0.04)]">
      {filtersPanel ? (
        <div className={isReadingOne ? "hidden lg:block" : ""}>
          {filtersPanel}
        </div>
      ) : null}

      {/*
       * A height of its own rather than the viewport's: this sits in the
       * middle of a page that goes on below it, so each column scrolls inside
       * a box the page can still be scrolled past.
       */}
      <div className="grid gap-5 lg:h-[40rem] lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:gap-0">
        <Card
          // Narrow screens show one at a time: the list, or the posting it
          // opened. Both columns are side by side once there is room.
          className={`flex min-h-0 flex-col lg:h-full lg:rounded-none lg:border-0 lg:shadow-none ${
            isReadingOne ? "hidden lg:flex" : ""
          }`}
        >
          <p
            className="shrink-0 border-b border-border px-4 py-3 text-sm text-text-muted"
            aria-live="polite"
          >
            Showing {formatCount(offset + 1)}&ndash;
            {formatCount(Math.min(offset + PAGE_SIZE, jobs.length))} of{" "}
            {formatCount(jobs.length)} matches
          </p>

          {/* No overscroll-contain, unlike the Jobs tab: that page is the
              list, so trapping the wheel in it is right. Here the list is one
              section of a result, and reaching its end should carry the
              reader on to the panels below rather than stop dead. */}
          <ul className="divide-y divide-border lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
            {pageJobs.map((job, index) => (
              <MatchRow
                // Title and company are not unique: one employer can post the
                // same role twice, which collided as a React key.
                key={job.job_id || `${job.title}-${job.company}-${index}`}
                job={job}
                isSelected={job.job_id === selected?.job_id}
                onSelect={() => openMatch(job)}
              />
            ))}
          </ul>

          {pageCount > 1 ? (
            <nav
              aria-label="Match list pages"
              className="flex shrink-0 items-center justify-between gap-2 border-t border-border px-4 py-3"
            >
              {currentPage > 0 ? (
                <button
                  type="button"
                  onClick={() => turnTo(currentPage - 1)}
                  className="shrink-0 text-sm font-medium text-accent hover:underline"
                >
                  Previous
                </button>
              ) : (
                <span />
              )}

              <div className="flex items-center gap-1">
                {pageWindow(currentPage + 1, pageCount).map((shown, index) =>
                  shown === "gap" ? (
                    <span
                      key={`gap-${index}`}
                      aria-hidden="true"
                      className="px-1 text-sm text-text-subtle"
                    >
                      &hellip;
                    </span>
                  ) : shown === currentPage + 1 ? (
                    <span
                      key={shown}
                      aria-current="page"
                      className="rounded-md bg-accent-fill px-2 py-1 text-sm font-medium text-on-accent"
                    >
                      {shown}
                    </span>
                  ) : (
                    <button
                      key={shown}
                      type="button"
                      onClick={() => turnTo(shown - 1)}
                      aria-label={`Page ${shown}`}
                      className="rounded-md px-2 py-1 text-sm text-text-muted transition-colors hover:bg-surface-muted hover:text-text"
                    >
                      {shown}
                    </button>
                  ),
                )}
              </div>

              {currentPage + 1 < pageCount ? (
                <button
                  type="button"
                  onClick={() => turnTo(currentPage + 1)}
                  className="shrink-0 text-sm font-medium text-accent hover:underline"
                >
                  Next
                </button>
              ) : (
                <span />
              )}
            </nav>
          ) : null}
        </Card>

        <div
          className={`min-w-0 lg:relative lg:h-full ${
            isReadingOne
              ? // Bleeds past the page padding so the posting sits on white
                // rather than the page's own ground.
                "-mx-5 rounded-none bg-surface px-5 py-2 sm:-mx-8 sm:px-8 lg:mx-0 lg:border-l lg:border-border lg:bg-transparent lg:p-0"
              : "hidden lg:block lg:border-l lg:border-border"
          }`}
        >
          <button
            type="button"
            onClick={() => setIsReadingOne(false)}
            className="mb-3 flex items-center gap-2 text-sm font-medium text-text-muted transition-colors hover:text-text lg:hidden"
          >
            <BackIcon />
            Back to matches
          </button>

          <div className="lg:absolute lg:inset-0 lg:overflow-hidden">
            {selected ? (
              <MatchDetail
                key={selected.job_id || selected.title}
                job={selected}
                datasetName={datasetName}
                isSaved={savedIds.has(selected.job_id)}
              />
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
