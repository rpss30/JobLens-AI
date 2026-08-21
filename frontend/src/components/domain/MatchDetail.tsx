"use client";

import { useEffect, useState } from "react";

import { BookmarkButton } from "@/components/domain/BookmarkButton";
import { CompanyLogo } from "@/components/domain/CompanyLogo";
import { JobDescription } from "@/components/domain/JobDescription";
import { ExperienceFitBadge, SkillTag } from "@/components/domain/MatchMarks";
import { CardSkeleton } from "@/components/ui/States";
import type { JobDetail, JobMatch } from "@/lib/api/types";
import { formatDate } from "@/lib/format";

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

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg bg-surface-muted px-2.5 py-1 text-xs text-text-muted">
      {children}
    </span>
  );
}

/**
 * One matched posting, read beside the list it was chosen from.
 *
 * The analysis carries everything about the match but not the posting's own
 * words, so those are fetched here. A failure leaves the match itself
 * readable rather than emptying the panel.
 */
export function MatchDetail({
  job,
  datasetName,
  isSaved,
}: {
  job: JobMatch;
  datasetName: string;
  isSaved: boolean;
}) {
  const [detail, setDetail] = useState<JobDetail | null>(null);
  /*
   * Opening another match remounts this panel on its key, so there is no
   * previous posting's state to clear here: it starts loading if there is an
   * id to load, and every write below happens once the request settles.
   */
  const [isLoading, setIsLoading] = useState(Boolean(job.job_id));

  useEffect(() => {
    if (!job.job_id) {
      return;
    }

    // Set on the way out, so a request still in flight for a panel that has
    // been replaced cannot write to the one that replaced it.
    let isStale = false;

    fetch(
      `/proxy/jobs/${encodeURIComponent(job.job_id)}?dataset_name=${encodeURIComponent(datasetName)}`,
    )
      .then((response) => (response.ok ? response.json() : null))
      .then((body: JobDetail | null) => {
        if (!isStale) {
          setDetail(body);
        }
      })
      .catch(() => undefined)
      .finally(() => {
        if (!isStale) {
          setIsLoading(false);
        }
      });

    return () => {
      isStale = true;
    };
  }, [job.job_id, datasetName]);

  const skills = [
    ...job.matched_skills.map((skill) => ({ skill, isMatched: true })),
    ...job.missing_skills.map((skill) => ({ skill, isMatched: false })),
  ];

  return (
    <div className="flex min-h-0 flex-col gap-4 lg:h-full">
      {/* Outside the scrolling part, so which posting is open and how well it
          fits stay readable however far down the description you are. */}
      <div className="shrink-0 space-y-4 border-b border-border pb-4 pt-1 lg:px-6 lg:pt-6">
        {/* The score stays level with the title at every width, because it
            is the one thing this panel says that the Jobs tab does not. The
            title wraps into what is left rather than pushing it down; the
            floor the Jobs tab puts under its title is for the buttons it
            keeps on this row, and those sit below here. The logo sits level
            with the middle of the title rather than at the top of it. */}
        <div className="flex items-center gap-3">
          <CompanyLogo
            name={job.company}
            domain={job.company_domain}
            size="title"
          />

          <div className="min-w-0 flex-1">
            {/* Two lines on a phone whatever the title is: held to two so a
                long one cannot push the score down, and given two so a short
                one does not leave the logo floating in a taller row. */}
            <h2 className="line-clamp-2 min-h-[2lh] text-lg font-semibold leading-snug text-text sm:line-clamp-none sm:min-h-0 sm:text-xl sm:font-medium">
              {job.title}
            </h2>
            <p className="mt-0.5 flex items-center gap-1.5 text-sm text-text-muted">
              <BuildingIcon />
              <span className="truncate">{job.company}</span>
            </p>
          </div>

          {/* Stacked on a phone so the pair takes a column rather than a
              line, which is the width the title needs. */}
          <p className="shrink-0 text-right sm:text-left">
            <span className="block text-2xl font-semibold tabular-nums text-text sm:inline">
              {Math.round(job.skill_match_score)}%
            </span>
            <span className="block text-xs text-text-muted sm:ml-1.5 sm:inline sm:text-sm">
              skill fit
            </span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* A dataset that never recorded an id has nothing to save
              against. */}
          {job.job_id ? (
            <BookmarkButton
              job={job}
              datasetName={datasetName}
              initiallySaved={isSaved}
            />
          ) : null}

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
          {job.role_category ? <Pill>{job.role_category}</Pill> : null}
          {job.experience_level ? <Pill>{job.experience_level}</Pill> : null}
        </div>

        {skills.length > 0 ? (
          <div>
            <h3 className="text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle">
              Skills this job asks for
            </h3>
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {skills.map(({ skill, isMatched }) => (
                <li key={skill}>
                  <SkillTag skill={skill} isMatched={isMatched} />
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {/* Under the skills rather than beside the score: both are ways this
            posting is or is not within reach, and they read together. */}
        <p className="flex flex-wrap items-center gap-2 text-sm text-text">
          <span className="text-text-muted">Experience Required:</span>
          {job.required_experience}
          <ExperienceFitBadge fit={job.experience_fit} />
        </p>
      </div>

      {/* Only a scroller once there is a height to scroll in, and without the
          overscroll-contain the Jobs tab uses: this panel sits above the rest
          of a result, so reaching the end of the description should carry on
          down the page rather than stop dead. */}
      <div className="min-h-0 pb-1 lg:flex-1 lg:overflow-y-auto lg:px-6 lg:pb-6">
        <h3 className="text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle">
          About the job
        </h3>
        <div className="mt-2">
          {isLoading ? (
            <CardSkeleton rows={6} />
          ) : detail ? (
            <JobDescription
              description={detail.description}
              formatted={detail.description_formatted}
            />
          ) : (
            <p className="text-sm text-text-muted">
              This posting&rsquo;s own description could not be loaded.
              {job.source_url ? " Open the original to read it." : ""}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
