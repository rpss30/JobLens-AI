import { Badge } from "@/components/ui/Badge";
import type { JobListing } from "@/lib/api/types";
import { formatDate, formatSkill } from "@/lib/format";

const MAX_VISIBLE_SKILLS = 8;

export function JobListingCard({ job }: { job: JobListing }) {
  const visibleSkills = job.skills.slice(0, MAX_VISIBLE_SKILLS);
  const hiddenSkillCount = job.skills.length - visibleSkills.length;
  const postedDate = formatDate(job.date_posted);

  return (
    <article className="rounded-xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-text">{job.title}</h3>
          <p className="mt-0.5 text-sm text-text-muted">{job.company}</p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {job.is_remote ? <Badge tone="accent">Remote</Badge> : null}
          <Badge tone="neutral">{job.role_category}</Badge>
        </div>
      </div>

      <ul className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-text-muted">
        <li>{job.location}</li>
        {job.experience_level ? (
          <>
            <li aria-hidden="true">·</li>
            <li>{job.experience_level}</li>
          </>
        ) : null}
        {job.employment_type ? (
          <>
            <li aria-hidden="true">·</li>
            <li>{job.employment_type}</li>
          </>
        ) : null}
        {postedDate ? (
          <>
            <li aria-hidden="true">·</li>
            <li>Posted {postedDate}</li>
          </>
        ) : null}
      </ul>

      {visibleSkills.length > 0 ? (
        <ul className="mt-4 flex flex-wrap gap-1.5">
          {visibleSkills.map((skill) => (
            <li key={skill}>
              <Badge tone="neutral">{formatSkill(skill)}</Badge>
            </li>
          ))}
          {hiddenSkillCount > 0 ? (
            <li>
              <span className="text-xs text-text-subtle">
                +{hiddenSkillCount} more
              </span>
            </li>
          ) : null}
        </ul>
      ) : null}

      {job.source_url ? (
        <a
          href={job.source_url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
        >
          View original posting
          <span className="sr-only">
            {" "}
            for {job.title} at {job.company}
          </span>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path
              d="M4.5 2h5.5v5.5M10 2L4 8M8 9.5v.5H2V4h.5"
              stroke="currentColor"
              strokeWidth="1.3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </a>
      ) : null}
    </article>
  );
}
