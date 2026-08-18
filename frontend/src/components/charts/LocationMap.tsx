/*
 * Posting counts as pins on a map of Canada.
 *
 * The outline is a MapSVG export drawn as one path per province; the pins are
 * placed from the export's own geoViewBox, so no mapping library is involved.
 *
 * The frame is cropped to the places that actually have postings. Drawn whole,
 * Canada is mostly arctic: two thirds of the height carries no posting at all
 * and squeezes every real city into a sliver along the bottom edge.
 *
 * Two crowding problems are solved deterministically, so the same data always
 * draws the same map: circles that would cover each other are displaced and
 * tied back to their city with a leader line, and a label with nowhere clear
 * to sit is dropped rather than overlapped. Dropping a label loses nothing —
 * the pin keeps its count and the ranked list beside the map names every
 * place.
 */

import Link from "next/link";

import {
  MAP_HEIGHT,
  MAP_WIDTH,
  PROVINCES,
  type Point,
  project,
} from "@/lib/geo/canadaMap";

export interface MapPin {
  label: string;
  value: number;
  at: Point;
  /** Where this place's postings live on the Jobs page. */
  href: string;
}

/** Room around the edge for circles and labels. */
const MARGIN = 26;
/*
 * Everything above this parallel is high arctic: a third of the drawing's
 * height, no postings in it, and it pushes the cities that do have postings
 * into a strip along the bottom. The rest of the country is kept whole.
 */
const TOP_LATITUDE = 79;

/** Sizes are quoted against this width and scaled with the crop. */
const REFERENCE_WIDTH = 800;
const MIN_RADIUS = 13;
const MAX_RADIUS = 44;
const STEP_COUNT = 5;
const LABEL_SIZE = 15;
const LABEL_HEIGHT = 20;
/** Close enough for collision tests at this font size. */
const LABEL_CHAR_WIDTH = 7.6;

interface Box {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

interface PlacedPin extends MapPin {
  /** Where the city actually is. */
  anchorX: number;
  anchorY: number;
  /** Where its circle ended up, once crowding was resolved. */
  x: number;
  y: number;
  radius: number;
  step: number;
  labelX?: number;
  labelY?: number;
  anchor?: "start" | "middle" | "end";
}

function overlaps(first: Box, second: Box): boolean {
  return !(
    first.right < second.left ||
    first.left > second.right ||
    first.bottom < second.top ||
    first.top > second.bottom
  );
}

export function LocationMap({ pins }: { pins: MapPin[] }) {
  if (pins.length === 0) {
    return (
      <p className="px-1 py-8 text-center text-sm text-text-muted">
        No postings in this dataset name a city that can be placed on the map.
      </p>
    );
  }

  const ranked = [...pins].sort((first, second) => second.value - first.value);
  const maxValue = ranked[0]?.value ?? 0;
  const anchors = ranked.map((pin) => project(pin.at));

  // A fixed crop, not one fitted to the data, so the country keeps its shape
  // and the map does not redraw itself at a new scale for every dataset. It
  // still opens up if a posting lands outside, so no pin can fall off.
  const frame = {
    minX: Math.min(-MARGIN, ...anchors.map((a) => a.x - MARGIN)),
    minY: Math.min(project([0, TOP_LATITUDE]).y, ...anchors.map((a) => a.y - MARGIN)),
    maxX: Math.max(MAP_WIDTH + MARGIN, ...anchors.map((a) => a.x + MARGIN)),
    maxY: Math.max(MAP_HEIGHT + MARGIN, ...anchors.map((a) => a.y + MARGIN)),
  };

  const frameWidth = frame.maxX - frame.minX;
  const frameHeight = frame.maxY - frame.minY;

  // Everything drawn on top of the map scales with the crop, so a tighter
  // frame does not turn the pins into blobs.
  const unit = frameWidth / REFERENCE_WIDTH;
  const labelSize = LABEL_SIZE * unit;
  const labelHeight = LABEL_HEIGHT * unit;
  const charWidth = LABEL_CHAR_WIDTH * unit;

  const radiusFor = (value: number) => {
    if (maxValue <= 0) {
      return MIN_RADIUS * unit;
    }

    // Area tracks the count, so twice the postings is twice the ink.
    const scaled = Math.sqrt(value / maxValue);

    return (MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * scaled) * unit;
  };

  const inFrame = (box: Box) =>
    box.left >= frame.minX &&
    box.right <= frame.maxX &&
    box.top >= frame.minY &&
    box.bottom <= frame.maxY;

  // Biggest first, so the busiest city keeps its true position and the
  // smaller ones move around it.
  const placed: PlacedPin[] = [];

  for (const [index, pin] of ranked.entries()) {
    const { x, y } = anchors[index];
    const radius = radiusFor(pin.value);

    const clashes = (candidateX: number, candidateY: number) =>
      placed.some(
        (other) =>
          Math.hypot(candidateX - other.x, candidateY - other.y) <
          radius + other.radius + 3 * unit,
      );

    let finalX = x;
    let finalY = y;

    if (clashes(x, y)) {
      search: for (let distance = radius; distance <= 240 * unit; distance += 4 * unit) {
        for (let turn = 0; turn < 24; turn += 1) {
          // Offsetting each pin's starting angle stops displaced circles
          // from lining up into a row.
          const angle = (turn * Math.PI * 2) / 24 + index * 0.9;
          const candidateX = x + Math.cos(angle) * distance;
          const candidateY = y + Math.sin(angle) * distance;

          const fits = inFrame({
            left: candidateX - radius,
            right: candidateX + radius,
            top: candidateY - radius,
            bottom: candidateY + radius,
          });

          if (fits && !clashes(candidateX, candidateY)) {
            finalX = candidateX;
            finalY = candidateY;
            break search;
          }
        }
      }
    }

    placed.push({
      ...pin,
      anchorX: x,
      anchorY: y,
      x: finalX,
      y: finalY,
      radius,
      step: Math.min(
        STEP_COUNT,
        1 + Math.floor((index / Math.max(ranked.length, 1)) * STEP_COUNT),
      ),
    });
  }

  // Circles claim their space before any label is placed, so a label never
  // lands on a pin.
  const taken: Box[] = placed.map((pin) => ({
    left: pin.x - pin.radius,
    right: pin.x + pin.radius,
    top: pin.y - pin.radius,
    bottom: pin.y + pin.radius,
  }));

  const directions: { dx: number; dy: number; anchor: PlacedPin["anchor"] }[] = [
    { dx: 0, dy: -1, anchor: "middle" },
    { dx: 1, dy: 0, anchor: "start" },
    { dx: -1, dy: 0, anchor: "end" },
    { dx: 0, dy: 1, anchor: "middle" },
    { dx: 0.7, dy: -0.7, anchor: "start" },
    { dx: -0.7, dy: -0.7, anchor: "end" },
    { dx: 0.7, dy: 0.7, anchor: "start" },
    { dx: -0.7, dy: 0.7, anchor: "end" },
  ];

  // Labels are placed biggest pin first, so the busiest city gets the pick of
  // the free space rather than losing out to a smaller neighbour.
  for (const pin of placed) {
    const width = pin.label.length * charWidth + 6 * unit;
    let settled = false;

    for (const spread of [0, 14, 30, 50]) {
      if (settled) {
        break;
      }

      for (const direction of directions) {
        const distance = pin.radius + (5 + spread) * unit;
        const x = pin.x + direction.dx * distance;
        const y =
          pin.y +
          direction.dy * distance +
          (direction.dy > 0
            ? labelHeight - 4 * unit
            : direction.dy < 0
              ? 0
              : 4 * unit);

        const left =
          direction.anchor === "start"
            ? x
            : direction.anchor === "end"
              ? x - width
              : x - width / 2;

        const box: Box = {
          left,
          right: left + width,
          top: y - labelHeight + 3 * unit,
          bottom: y + 3 * unit,
        };

        if (inFrame(box) && !taken.some((other) => overlaps(box, other))) {
          pin.labelX = x;
          pin.labelY = y;
          pin.anchor = direction.anchor;
          taken.push(box);
          settled = true;
          break;
        }
      }
    }
  }

  return (
    <svg
      viewBox={`${frame.minX} ${frame.minY} ${frameWidth} ${frameHeight}`}
      className="h-full w-full"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`Postings by location on a map of Canada. ${placed
        .map((pin) => `${pin.label}, ${pin.value}`)
        .join(". ")}`}
    >
      {PROVINCES.map((province) => (
        <path
          key={province.id}
          d={province.d}
          fill="var(--color-surface-muted)"
          stroke="var(--color-border)"
          strokeWidth={unit}
          strokeLinejoin="round"
        >
          <title>{province.title}</title>
        </path>
      ))}

      {/* Leader lines sit under every circle, so none is drawn across a pin. */}
      {placed.map((pin) =>
        Math.hypot(pin.x - pin.anchorX, pin.y - pin.anchorY) > 1 ? (
          <g key={`${pin.label}-leader`}>
            <line
              x1={pin.anchorX}
              y1={pin.anchorY}
              x2={pin.x}
              y2={pin.y}
              stroke="var(--color-chart-3)"
              strokeWidth={unit}
            />
            <circle
              cx={pin.anchorX}
              cy={pin.anchorY}
              r={2.5 * unit}
              fill="var(--color-chart-3)"
            />
          </g>
        ) : null,
      )}

      {placed.map((pin) => (
        <Link
          key={pin.label}
          href={pin.href}
          aria-label={`${pin.label}, ${pin.value} postings. Show these jobs.`}
          className="cursor-pointer outline-none [&:focus-visible>circle]:stroke-accent [&:hover>circle]:stroke-accent"
        >
          {pin.labelX !== undefined && pin.labelY !== undefined ? (
            <text
              x={pin.labelX}
              y={pin.labelY}
              textAnchor={pin.anchor}
              fontSize={labelSize}
              fill="var(--color-text-muted)"
            >
              {pin.label}
            </text>
          ) : null}
          <circle
            cx={pin.x}
            cy={pin.y}
            r={pin.radius}
            fill={`var(--color-chart-${pin.step})`}
            stroke="var(--color-surface)"
            strokeWidth={1.5 * unit}
          />
          {pin.radius >= 12 * unit ? (
            <text
              x={pin.x}
              y={pin.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={Math.min(20 * unit, pin.radius * 0.72)}
              fontWeight={600}
              fill={
                pin.step <= 3
                  ? "var(--color-surface)"
                  : "var(--color-on-accent)"
              }
            >
              {pin.value}
            </text>
          ) : null}
        </Link>
      ))}
    </svg>
  );
}
