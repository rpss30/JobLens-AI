/*
 * A packed-circle view of skill demand.
 *
 * Hand-drawn rather than pulled from a charting library: Recharts has no
 * circle-packing layout, and the frontend deliberately carries no extra
 * component dependencies. The layout is deterministic, so the same data always
 * produces the same picture rather than shuffling between renders.
 */

export interface BubbleDatum {
  label: string;
  value: number;
}

interface PlacedBubble extends BubbleDatum {
  x: number;
  y: number;
  radius: number;
  step: number;
}

const VIEWBOX = 520;
const CENTER = VIEWBOX / 2;
const MIN_RADIUS = 26;
const MAX_RADIUS = 84;
const GAP = 4;

/** Steps 1-3 are dark enough to need light text; 4 and 5 take dark text. */
const STEP_COUNT = 5;

function radiusFor(value: number, maxValue: number, scale: number): number {
  if (maxValue <= 0) {
    return MIN_RADIUS * scale;
  }

  // Area, not radius, tracks the count: doubling a bar's length is honest,
  // doubling a circle's radius quadruples the ink for twice the value.
  const scaled = Math.sqrt(value / maxValue);

  return (MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * scaled) * scale;
}

function overlaps(candidate: PlacedBubble, placed: PlacedBubble[]): boolean {
  return placed.some((other) => {
    const distance = Math.hypot(candidate.x - other.x, candidate.y - other.y);

    return distance < candidate.radius + other.radius + GAP;
  });
}

/**
 * Largest circle in the middle, the rest spiralled outward into the first
 * position that does not collide.
 *
 * Returns null when anything failed to fit, so the caller can shrink and try
 * again rather than quietly dropping a skill off the chart.
 */
function tryLayout(data: BubbleDatum[], scale: number): PlacedBubble[] | null {
  const ranked = [...data].sort((first, second) => second.value - first.value);
  const maxValue = ranked[0]?.value ?? 0;
  const placed: PlacedBubble[] = [];

  for (const [index, datum] of ranked.entries()) {
    const radius = radiusFor(datum.value, maxValue, scale);
    const step = Math.min(
      STEP_COUNT,
      1 + Math.floor((index / Math.max(ranked.length, 1)) * STEP_COUNT),
    );

    if (index === 0) {
      placed.push({ ...datum, x: CENTER, y: CENTER, radius, step });
      continue;
    }

    let positioned = false;

    for (
      let distance = radius + 8;
      distance <= CENTER - radius && !positioned;
      distance += 4
    ) {
      // Offsetting each ring stops the circles lining up into spokes.
      const offset = (index * 137.5 * Math.PI) / 180;

      for (let turn = 0; turn < 36; turn += 1) {
        const angle = offset + (turn * Math.PI * 2) / 36;
        const candidate = {
          ...datum,
          radius,
          step,
          x: CENTER + Math.cos(angle) * distance,
          y: CENTER + Math.sin(angle) * distance,
        };

        const insideBounds =
          candidate.x - radius >= 0 &&
          candidate.x + radius <= VIEWBOX &&
          candidate.y - radius >= 0 &&
          candidate.y + radius <= VIEWBOX;

        if (insideBounds && !overlaps(candidate, placed)) {
          placed.push(candidate);
          positioned = true;
          break;
        }
      }
    }

    if (!positioned) {
      return null;
    }
  }

  return placed;
}

/** Shrinks until every skill fits, so none is silently left out. */
function layout(data: BubbleDatum[]): PlacedBubble[] {
  for (let attempt = 0; attempt < 12; attempt += 1) {
    const placed = tryLayout(data, 1 - attempt * 0.06);

    if (placed) {
      return placed;
    }
  }

  return tryLayout(data, 0.3) ?? [];
}

export function SkillBubbleChart({
  data,
  valueLabel,
}: {
  data: BubbleDatum[];
  valueLabel: string;
}) {
  const bubbles = layout(data);

  if (bubbles.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        No skills were recorded for this dataset.
      </p>
    );
  }

  return (
    <svg
      viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}
      className="h-auto w-full"
      role="img"
      aria-label={`Skill demand by ${valueLabel}. ${bubbles
        .map((bubble) => `${bubble.label}, ${bubble.value}`)
        .join(". ")}`}
    >
      {bubbles.map((bubble) => {
        const textColor =
          bubble.step <= 3 ? "var(--color-surface)" : "var(--color-on-accent)";
        const labelSize = Math.max(9, Math.min(15, bubble.radius / 4.6));
        // Long names need the room a single line cannot give them.
        const words = bubble.label.split(" ");
        const lines =
          words.length > 1 && bubble.radius > 40
            ? [words.slice(0, -1).join(" "), words[words.length - 1]]
            : [bubble.label];
        const showLabel = bubble.radius >= 30;

        return (
          <g
            key={bubble.label}
            /*
             * fill-box makes the circle grow about its own centre; without it
             * an SVG transform pivots on the viewBox origin and the bubble
             * slides across the chart instead of swelling in place.
             */
            className="origin-center [transform-box:fill-box] motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-out motion-safe:hover:scale-[1.06]"
          >
            <circle
              cx={bubble.x}
              cy={bubble.y}
              r={bubble.radius}
              fill={`var(--color-chart-${bubble.step})`}
            />
            {showLabel ? (
              <text
                x={bubble.x}
                y={bubble.y}
                textAnchor="middle"
                fill={textColor}
                fontSize={labelSize}
                fontWeight={500}
              >
                {lines.map((line, lineIndex) => (
                  <tspan
                    key={line}
                    x={bubble.x}
                    dy={lineIndex === 0 ? `${-0.2 * lines.length}em` : "1.1em"}
                  >
                    {line}
                  </tspan>
                ))}
                <tspan
                  x={bubble.x}
                  dy="1.35em"
                  fontSize={labelSize * 1.15}
                  fontWeight={600}
                >
                  {bubble.value}
                </tspan>
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}
