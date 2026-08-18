import type { RoleSkillImportance } from "@/lib/api/types";

/*
 * One definition of what each requirement signal means and what colour marks
 * it, shared by the legend and the tags it explains. Kept together so a tag
 * can never carry a colour the legend does not account for.
 */
export const REQUIREMENT_SIGNAL: Record<
  RoleSkillImportance["requirement_signal"],
  { label: string; hint: string; color: string }
> = {
  required: {
    label: "Usually required",
    hint: "Requirement in most postings that mention it",
    color: "var(--color-signal-required)",
  },
  preferred: {
    label: "Usually preferred",
    hint: "Bonus more often than a requirement",
    color: "var(--color-signal-preferred)",
  },
  mixed: {
    label: "Mixed",
    hint: "Varies between required or preferred",
    color: "var(--color-signal-mixed)",
  },
  unclear: {
    label: "Not stated",
    hint: "Rarely specified",
    color: "var(--color-signal-unclear)",
  },
};

export function SignalDot({ color }: { color: string }) {
  return (
    <span
      // inline-block, or width and height do not apply and the dot vanishes.
      className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
      style={{ backgroundColor: color }}
      aria-hidden="true"
    />
  );
}

/** The key for the tags below it, sharing a card with the panel itself. */
export function RequirementLegend() {
  return (
    <dl className="grid gap-x-5 gap-y-3 text-xs sm:grid-cols-2">
      {Object.values(REQUIREMENT_SIGNAL).map((signal) => (
        <div key={signal.label} className="flex items-start gap-2">
          <span className="mt-1 flex">
            <SignalDot color={signal.color} />
          </span>
          <div>
            <dt className="font-medium text-text">{signal.label}</dt>
            <dd className="text-text-subtle">{signal.hint}</dd>
          </div>
        </div>
      ))}
    </dl>
  );
}
