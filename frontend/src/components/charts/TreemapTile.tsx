"use client";

import { useState } from "react";

import { CategoryIcon } from "@/components/charts/CategoryIcons";
import { formatCount } from "@/lib/format";

interface TreemapTileProps {
  label: string;
  value: number;
  share: number;
  /** Percent position within the chart, used to decide which way to open. */
  top: number;
  showIcon: boolean;
  showShare: boolean;
  isLargest: boolean;
  step: number;
}

/**
 * One treemap tile, with the full figures on tap.
 *
 * A narrow tile truncates its category name, and a title attribute would only
 * help a mouse: touch devices never hover. So the tile is a button that opens
 * a small panel on tap, hover, or focus, which also gives keyboard users a way
 * to read a tile too small to label.
 */
export function TreemapTile({
  label,
  value,
  share,
  top,
  showIcon,
  showShare,
  isLargest,
  step,
}: TreemapTileProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Tiles near the ceiling open downward, or the panel would be clipped by
  // the top of the chart.
  const opensBelow = top < 25;

  return (
    <div
      // Lifted while hovered so the tile that grows sits over its neighbours
      // rather than under whichever happens to be drawn later.
      className="relative h-full w-full hover:z-10"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button
        type="button"
        aria-expanded={isOpen}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        onClick={() => setIsOpen((open) => !open)}
        className={`flex h-full w-full flex-col overflow-hidden rounded-xl p-3 text-left motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-out motion-safe:hover:scale-[1.03] sm:p-4 ${
          step <= 3 ? "text-white" : "text-on-accent"
        }`}
        style={{ backgroundColor: `var(--color-chart-${step})` }}
      >
        {showIcon ? (
          <span className="mb-2 inline-flex w-fit rounded-lg bg-white/20 p-2">
            <CategoryIcon category={label} />
          </span>
        ) : null}

        {/* shrink-0 or flex collapses these to nothing on a short tile,
            leaving a number with no name beside it. */}
        <p className="shrink-0 truncate text-sm font-medium sm:text-base">
          {label}
        </p>
        <p className="shrink-0 text-2xl font-semibold tabular-nums sm:text-3xl">
          {formatCount(value)}
        </p>

        {showShare ? (
          <span className="mt-1.5 w-fit rounded-md bg-white/20 px-1.5 py-0.5 text-xs font-medium tabular-nums">
            {Math.round(share * 100)}%
          </span>
        ) : null}

        {isLargest ? (
          <span className="mt-auto text-sm opacity-80">postings</span>
        ) : null}
      </button>

      {isOpen ? (
        <span
          role="tooltip"
          className={`pointer-events-none absolute left-1/2 z-20 w-max max-w-[12rem] -translate-x-1/2 rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lg ${
            opensBelow ? "top-full mt-1" : "bottom-full mb-1"
          }`}
        >
          <strong className="block font-medium text-text">{label}</strong>
          <span className="text-text-muted">
            {formatCount(value)} postings · {Math.round(share * 100)}%
          </span>
        </span>
      ) : null}
    </div>
  );
}
