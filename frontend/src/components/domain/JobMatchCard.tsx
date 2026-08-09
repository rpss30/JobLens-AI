import { Badge } from "@/components/ui/Badge";
import type { JobMatch } from "@/lib/api/types";
import { formatSkill, parseSkillPreview } from "@/lib/format";

function SkillChips({
  label,
  skills,
  tone,
}: {
  label: string;
  skills: string[];
  tone: "positive" | "warning";
}) {
  if (skills.length === 0) {
    return null;
  }

  return (
    <div className="min-w-0">
      <p className="text-xs font-medium uppercase tracking-wide text-text-subtle">
        {label}
      </p>
      <ul className="mt-1.5 flex flex-wrap gap-1.5">
        {skills.map((skill) => (
          <li key={skill}>
            <Badge tone={tone}>{formatSkill(skill)}</Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function JobMatchCard({ job }: { job: JobMatch }) {
  const matchedSkills = parseSkillPreview(job.matched_skills_preview);
  const missingSkills = parseSkillPreview(job.missing_skills_preview);

  return (
    <article className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-text">{job.title}</h3>
          <p className="mt-0.5 text-sm text-text-muted">{job.company}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-2xl font-semibold tabular-nums text-text">
            {Math.round(job.job_match_score)}%
          </p>
          <p className="text-xs text-text-subtle">skill fit</p>
        </div>
      </div>

      <ul className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-text-muted">
        <li>{job.location}</li>
        <li aria-hidden="true">·</li>
        <li>{job.experience_level}</li>
        <li aria-hidden="true">·</li>
        <li>{job.role_category}</li>
      </ul>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <SkillChips label="Matched" skills={matchedSkills} tone="positive" />
        <SkillChips label="Missing" skills={missingSkills} tone="warning" />
      </div>

      {job.source_url ? (
        <a
          href={job.source_url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-accent hover:underline"
        >
          View original posting
          <span className="sr-only"> for {job.title} at {job.company}</span>
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
