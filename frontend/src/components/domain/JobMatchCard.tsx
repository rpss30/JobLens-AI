import { Badge, type BadgeTone } from "@/components/ui/Badge";
import type { JobMatch } from "@/lib/api/types";
import { formatSkill, parseSkillPreview } from "@/lib/format";

function SkillChips({
  label,
  skills,
  tone,
}: {
  label: string;
  skills: string[];
  tone: BadgeTone;
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

function getExperienceTone(fit: string): BadgeTone {
  if (fit === "Meets requirement") {
    return "positive";
  }

  if (fit === "Close match") {
    return "accent";
  }

  if (fit === "Stretch") {
    return "warning";
  }

  return "neutral";
}

export function JobMatchCard({ job }: { job: JobMatch }) {
  const matchedSkills = parseSkillPreview(job.matched_skills_preview);
  const missingSkills = parseSkillPreview(job.missing_skills_preview);
  const skillMatchScore = job.skill_match_score ?? job.job_match_score;
  // Presence is judged on whether there are skills to show, not on whether a
  // coverage figure came back: a job can report 0% preferred coverage while
  // listing no preferred skills at all, which would open an empty section.
  const hasRequiredSkillExplanation =
    job.matched_required_skills.length > 0 ||
    job.missing_required_skills.length > 0;
  const hasPreferredSkillExplanation =
    job.matched_preferred_skills.length > 0 ||
    job.missing_preferred_skills.length > 0;

  // The summary names only what is actually inside it.
  const skillExplanationLabel =
    hasRequiredSkillExplanation && hasPreferredSkillExplanation
      ? "View required and preferred details"
      : hasRequiredSkillExplanation
        ? "View required skill details"
        : "View preferred skill details";

  return (
    <article className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-text">{job.title}</h3>
          <p className="mt-0.5 text-sm text-text-muted">{job.company}</p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-2xl font-semibold tabular-nums text-text">
            {Math.round(skillMatchScore)}%
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

      <div className="mt-4 rounded-lg border border-border bg-surface-muted p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-text-subtle">
            Experience fit
          </p>
          <Badge tone={getExperienceTone(job.experience_fit)}>
            {job.experience_fit}
          </Badge>
        </div>
        <p className="mt-2 text-sm text-text-muted">
          Candidate: {job.candidate_experience}
          <span aria-hidden="true"> · </span>
          Required: {job.required_experience}
        </p>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <SkillChips label="Matched" skills={matchedSkills} tone="positive" />
        <SkillChips label="Missing" skills={missingSkills} tone="warning" />
      </div>

      {hasRequiredSkillExplanation || hasPreferredSkillExplanation ? (
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-accent hover:underline">
            {skillExplanationLabel}
          </summary>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {hasRequiredSkillExplanation ? (
              <div className="space-y-3">
                <SkillChips
                  label="Matched required"
                  skills={job.matched_required_skills}
                  tone="positive"
                />
                <SkillChips
                  label="Missing required"
                  skills={job.missing_required_skills}
                  tone="warning"
                />
              </div>
            ) : null}

            {hasPreferredSkillExplanation ? (
              <div className="space-y-3">
                {job.preferred_skill_coverage !== null ? (
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-text-subtle">
                      Preferred coverage
                    </p>
                    <p className="mt-1 text-sm font-medium text-text">
                      {Math.round(job.preferred_skill_coverage)}%
                    </p>
                  </div>
                ) : null}
                <SkillChips
                  label="Matched preferred"
                  skills={job.matched_preferred_skills}
                  tone="accent"
                />
                <SkillChips
                  label="Missing preferred"
                  skills={job.missing_preferred_skills}
                  tone="warning"
                />
              </div>
            ) : null}
          </div>
        </details>
      ) : null}

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
