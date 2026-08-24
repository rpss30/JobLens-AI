"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";

export interface JobSortOption {
  value: string;
  label: string;
  /** Omitted where the list being ordered is not in the URL. */
  href?: string;
}

/**
 * The order the list is read in, chosen beside the heading.
 *
 * A details element rather than a listbox: where the choices are links the
 * order lives in the URL like every other filter, and the menu opens without
 * any client JavaScript. A matched-jobs result has no URL to live in, so it
 * passes onSelect instead and the same menu draws buttons.
 */
export function JobSortMenu({
  options,
  value,
  onSelect,
}: {
  options: JobSortOption[];
  value: string;
  onSelect?: (value: string) => void;
}) {
  const menuRef = useRef<HTMLDetailsElement | null>(null);

  /*
   * A details element only closes from its own summary, so a menu left open
   * follows the reader around the page. Closing it here rather than holding
   * the open state in React keeps the markup working before hydration, which
   * is the reason the menu is a details element in the first place.
   */
  useEffect(() => {
    const closeFromOutside = (event: Event) => {
      const menu = menuRef.current;

      if (menu?.open && !menu.contains(event.target as Node)) {
        menu.open = false;
      }
    };

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && menuRef.current?.open) {
        menuRef.current.open = false;
      }
    };

    document.addEventListener("pointerdown", closeFromOutside);
    document.addEventListener("keydown", closeOnEscape);

    return () => {
      document.removeEventListener("pointerdown", closeFromOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  const selected = options.find((option) => option.value === value) ?? options[0];
  // The first option is the order the list arrives in, so anything else is a
  // choice someone made and worth marking as one.
  const isReordered = Boolean(options[0]) && value !== options[0].value;

  return (
    <details ref={menuRef} className="group relative">
      <summary
        className={`inline-flex cursor-pointer list-none items-center gap-2 rounded-lg border px-3.5 py-2 text-sm transition-colors [&::-webkit-details-marker]:hidden ${
          isReordered
            ? "border-transparent bg-accent-fill text-on-accent hover:bg-accent-fill-hover"
            : "border-border bg-surface text-text hover:bg-surface-muted"
        }`}
      >
        {/* Narrow screens have no room to spell the field out, so they name
            it only once it is not the order the list came in. */}
        <span className="lg:hidden">{isReordered ? selected?.label : "Sort"}</span>
        <span className="hidden lg:inline">
          <span className="text-text-muted">Sort by: </span>
          {selected?.label}
        </span>
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
          className={isReordered ? "" : "text-text-muted"}
        >
          <path d="m6.75 8.25 3.25-3.25 3.25 3.25" />
          <path d="m6.75 11.75 3.25 3.25 3.25-3.25" />
        </svg>
      </summary>

      {/* Hangs from whichever edge the control sits against: anchored right
          on a narrow screen it ran off the side of the page. */}
      <div className="absolute left-0 z-30 mt-2 w-52 overflow-hidden rounded-xl border border-border bg-surface py-1.5 shadow-[0_12px_28px_rgba(16,21,31,0.14)] lg:left-auto lg:right-0">
        {options.map((option) => {
          const itemClassName = `block w-full px-4 py-2.5 text-left text-sm transition-colors ${
            option.value === value
              ? "bg-accent-soft text-text"
              : "text-text hover:bg-surface-muted"
          }`;

          return option.href ? (
            <Link
              key={option.value}
              href={option.href}
              aria-current={option.value === value ? "true" : undefined}
              className={itemClassName}
            >
              {option.label}
            </Link>
          ) : (
            <button
              key={option.value}
              type="button"
              aria-current={option.value === value ? "true" : undefined}
              onClick={() => {
                onSelect?.(option.value);

                if (menuRef.current) {
                  menuRef.current.open = false;
                }
              }}
              className={itemClassName}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </details>
  );
}
