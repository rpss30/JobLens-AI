import type { ReactNode } from "react";

/**
 * Every chart ships a table view so values are never gated behind hover or
 * color perception.
 */
export function TableDisclosure({
  label = "View as table",
  children,
}: {
  label?: string;
  children: ReactNode;
}) {
  return (
    <details className="group border-t border-border">
      <summary className="cursor-pointer list-none px-5 py-3 text-sm font-medium text-text-muted hover:text-text">
        <span className="inline-flex items-center gap-1.5">
          <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
            aria-hidden="true"
            className="transition-transform group-open:rotate-90"
          >
            <path
              d="M3 1.5L7 5l-4 3.5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          {label}
        </span>
      </summary>
      <div className="pb-2">{children}</div>
    </details>
  );
}
