/*
 * How the work is done, as one ring per kind.
 *
 * Each ring is filled by that kind's share of every posting in the slice, so
 * the three read against the same whole rather than against each other.
 */

import type { CSSProperties } from "react";

import { formatCount } from "@/lib/format";

export interface WorkplaceDatum {
  workplace_type: string;
  job_count: number;
}

const SIZE = 84;
const STROKE = 8;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Read in this order whatever order the API sends them in. */
const ORDER = ["On-site", "Remote", "Hybrid", "Not stated"];

const RING_COLORS: Record<string, string> = {
  "On-site": "var(--color-chart-2)",
  Remote: "var(--color-chart-3)",
  Hybrid: "var(--color-chart-4)",
  "Not stated": "var(--color-chart-5)",
};

export function WorkplaceRadials({
  data,
  total,
}: {
  data: WorkplaceDatum[];
  total: number;
}) {
  const ordered = [...data].sort((first, second) => {
    const firstRank = ORDER.indexOf(first.workplace_type);
    const secondRank = ORDER.indexOf(second.workplace_type);

    return (
      (firstRank === -1 ? ORDER.length : firstRank) -
      (secondRank === -1 ? ORDER.length : secondRank)
    );
  });

  return (
    <ul className="flex w-full flex-wrap items-center justify-around gap-4">
      {ordered.map((item) => {
        const share = total > 0 ? item.job_count / total : 0;

        return (
          <li
            key={item.workplace_type}
            className="flex flex-col items-center gap-1.5"
          >
            <span className="relative inline-flex">
              <svg
                width={SIZE}
                height={SIZE}
                viewBox={`0 0 ${SIZE} ${SIZE}`}
                role="img"
                aria-label={`${item.workplace_type}, ${item.job_count} of ${total} postings`}
              >
                {/* Turned so the ring starts at the top. */}
                <g transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}>
                  <circle
                    cx={SIZE / 2}
                    cy={SIZE / 2}
                    r={RADIUS}
                    fill="none"
                    stroke="var(--color-surface-muted)"
                    strokeWidth={STROKE}
                  />
                  <circle
                    cx={SIZE / 2}
                    cy={SIZE / 2}
                    r={RADIUS}
                    fill="none"
                    stroke={
                      RING_COLORS[item.workplace_type] ?? "var(--color-chart-5)"
                    }
                    strokeWidth={STROKE}
                    strokeLinecap="round"
                    strokeDasharray={CIRCUMFERENCE}
                    strokeDashoffset={CIRCUMFERENCE * (1 - share)}
                    className="animate-ring-fill"
                    style={
                      {
                        "--ring-circumference": CIRCUMFERENCE,
                      } as CSSProperties
                    }
                  />
                </g>
                <text
                  x={SIZE / 2}
                  y={SIZE / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={19}
                  fontWeight={600}
                  fill="var(--color-text)"
                >
                  {formatCount(item.job_count)}
                </text>
              </svg>
            </span>
            <span className="text-xs text-text-muted">
              {item.workplace_type}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
