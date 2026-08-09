"use client";

import { useId, useState, type ReactNode } from "react";

/**
 * Reveals an explanation on hover, focus, or tap. Focus and click are handled
 * as well as hover so it is reachable by keyboard and on touch devices.
 */
export function InfoTooltip({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const tooltipId = useId();

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        type="button"
        aria-describedby={isOpen ? tooltipId : undefined}
        aria-expanded={isOpen}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        onClick={() => setIsOpen((open) => !open)}
        className="inline-flex items-center gap-1 rounded-md border border-border bg-surface-muted px-2 py-0.5 text-xs font-medium text-text-muted hover:text-text"
      >
        {label}
        <svg width="11" height="11" viewBox="0 0 12 12" fill="none" aria-hidden="true">
          <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" />
          <path
            d="M6 5.2v3M6 3.6v.1"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
        <span className="sr-only">More information</span>
      </button>

      {isOpen ? (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute right-0 top-full z-30 mt-2 w-72 rounded-lg border border-border bg-surface p-3 text-left text-xs leading-relaxed font-normal text-text-muted shadow-lg"
        >
          {children}
        </span>
      ) : null}
    </span>
  );
}
