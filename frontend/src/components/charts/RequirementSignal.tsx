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
    label: "Required",
    hint: "Requirement in most postings that mention it",
    color: "var(--color-signal-required)",
  },
  preferred: {
    label: "Preferred",
    hint: "Bonus more often than a requirement",
    color: "var(--color-signal-preferred)",
  },
  mixed: {
    label: "Mixed",
    hint: "Varies between required or preferred",
    color: "var(--color-signal-mixed)",
  },
  unclear: {
    label: "Unclear",
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
    // Four across where there is room, two where there is not. The mark sits
    // above its name rather than beside it, so the names line up as a row.
    <dl className="grid grid-cols-2 gap-x-5 gap-y-5 text-xs sm:grid-cols-4">
      {Object.values(REQUIREMENT_SIGNAL).map((signal) => (
        <div key={signal.label}>
          <SignalDot color={signal.color} />
          <dt className="mt-2 text-sm font-medium text-text">{signal.label}</dt>
          <dd className="mt-1 text-text-subtle">{signal.hint}</dd>
        </div>
      ))}
    </dl>
  );
}
