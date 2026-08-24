"use client";

import { useId, useRef, useState, type ReactNode } from "react";

/**
 * Reveals an explanation on hover, focus, or tap. Focus and click are handled
 * as well as hover so it is reachable by keyboard and on touch devices.
 */
const triggerStyles = {
  // A standalone control, such as the dataset name on the overview.
  chip: "rounded-md border border-border bg-surface-muted px-2 py-0.5 text-xs font-medium text-text-muted hover:text-text",
  // Sits inline beside other status text, so it carries no chrome of its own.
  plain: "rounded text-xs font-medium text-text-muted hover:text-text",
};

/*
 * Enough room for the longest explanation in the app. The panel is measured
 * against this before it opens rather than after, so it never paints below the
 * fold and jumps: triggers low on the page, such as the connection indicator
 * at the foot of the sidebar, open upward instead.
 */
const ESTIMATED_PANEL_HEIGHT = 200;

export function InfoTooltip({
  label,
  variant = "chip",
  align = "end",
  children,
}: {
  label: ReactNode;
  variant?: keyof typeof triggerStyles;
  /** "start" opens the panel rightward, for triggers near the left edge. */
  align?: "start" | "end";
  children: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [side, setSide] = useState<"top" | "bottom">("bottom");
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipId = useId();

  function open() {
    const trigger = triggerRef.current?.getBoundingClientRect();

    setSide(
      trigger && window.innerHeight - trigger.bottom < ESTIMATED_PANEL_HEIGHT
        ? "top"
        : "bottom",
    );
    setIsOpen(true);
  }

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={open}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-describedby={isOpen ? tooltipId : undefined}
        aria-expanded={isOpen}
        onFocus={open}
        onBlur={() => setIsOpen(false)}
        onClick={() => (isOpen ? setIsOpen(false) : open())}
        className={`inline-flex items-center gap-1 ${triggerStyles[variant]}`}
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
          className={`absolute z-30 w-72 rounded-lg border border-border bg-surface p-3 text-left text-xs leading-relaxed font-normal text-text-muted shadow-lg ${
            side === "top" ? "bottom-full mb-2" : "top-full mt-2"
          } ${align === "start" ? "left-0" : "right-0"}`}
        >
          {children}
        </span>
      ) : null}
    </span>
  );
}
