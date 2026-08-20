import Link from "next/link";

export interface JobSortOption {
  value: string;
  label: string;
  href: string;
}

/**
 * The order the list is read in, chosen beside the heading.
 *
 * A details element rather than a listbox: the choices are links, so the
 * order lives in the URL like every other filter, and the menu opens without
 * any client JavaScript.
 */
export function JobSortMenu({
  options,
  value,
}: {
  options: JobSortOption[];
  value: string;
}) {
  const selected = options.find((option) => option.value === value) ?? options[0];

  return (
    <details className="group relative">
      <summary className="inline-flex cursor-pointer list-none items-center gap-2 rounded-lg border border-border bg-surface px-3.5 py-2 text-sm text-text transition-colors hover:bg-surface-muted [&::-webkit-details-marker]:hidden">
        <span className="text-text-muted">Sort by:</span>
        {selected?.label}
        {/* Two chevrons: the control reorders, it does not simply expand. */}
        <svg
          width="14"
          height="14"
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="text-text-muted"
        >
          <path d="m6.75 8.25 3.25-3.25 3.25 3.25" />
          <path d="m6.75 11.75 3.25 3.25 3.25-3.25" />
        </svg>
      </summary>

      <div className="absolute right-0 z-30 mt-2 w-52 overflow-hidden rounded-xl border border-border bg-surface py-1.5 shadow-[0_12px_28px_rgba(16,21,31,0.14)]">
        {options.map((option, index) => (
          <Link
            key={option.value}
            href={option.href}
            aria-current={option.value === value ? "true" : undefined}
            // The rule is inset and belongs to the row above, so a highlighted
            // row reads as one unbroken band rather than a boxed-in cell.
            className={`relative block px-4 py-2.5 text-sm transition-colors ${
              index > 0
                ? "before:absolute before:inset-x-4 before:top-0 before:h-px before:bg-border before:content-['']"
                : ""
            } ${
              option.value === value
                ? "bg-accent-soft text-text before:hidden"
                : "text-text hover:bg-surface-muted"
            }`}
          >
            {option.label}
          </Link>
        ))}
      </div>
    </details>
  );
}
