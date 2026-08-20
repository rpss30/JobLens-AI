import { formatSkill } from "@/lib/format";
import { experienceFitLabel } from "@/lib/matches";

/**
 * The two marks that make a matched posting different from a browsed one:
 * how far its experience requirement is out of reach, and which of the skills
 * it asks for the reader already has.
 */

const fitStyles: Record<string, string> = {
  "Meets requirement": "border-fit-met bg-fit-met-soft text-fit-met",
  "Close match": "border-fit-close bg-fit-close-soft text-fit-close",
  Stretch: "border-fit-stretch bg-fit-stretch-soft text-fit-stretch",
};

export function ExperienceFitBadge({ fit }: { fit: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${
        fitStyles[fit] ?? "border-border bg-surface-muted text-text-muted"
      }`}
    >
      {experienceFitLabel(fit)}
    </span>
  );
}

/**
 * One skill the posting asks for.
 *
 * Filled means the candidate has it and outlined means they do not, which is
 * the whole reading: how much of the job is already coloured in. The two are
 * not told apart by colour alone — the outline is dashed.
 */
export function SkillTag({
  skill,
  isMatched,
}: {
  skill: string;
  isMatched: boolean;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${
        isMatched
          ? "border-transparent bg-match text-on-match"
          : "border-dashed border-border-strong bg-transparent text-text-subtle"
      }`}
    >
      {formatSkill(skill)}
    </span>
  );
}
