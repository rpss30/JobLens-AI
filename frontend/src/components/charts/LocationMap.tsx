/*
 * Posting counts as pins on a map of the United States and Canada.
 *
 * The outline is a MapSVG export drawn as one path per state and province;
 * the pins are placed from the export's own geoViewBox, so no mapping library
 * is involved.
 *
 * The frame is cropped to the band the postings sit in. Drawn whole, the
 * export runs from the Aleutians to Newfoundland and from the high arctic to
 * southern Mexico: Alaska alone takes two fifths of the width, and most of
 * the height carries no posting at all.
 *
 * Two crowding problems are solved deterministically, so the same data always
 * draws the same map: circles that would cover each other are displaced and
 * tied back to their city with a leader line, and a label with nowhere clear
 * to sit is dropped rather than overlapped. Dropping a label loses nothing —
 * the pin keeps its count and the ranked list beside the map names every
 * place.
 */

import type { CSSProperties } from "react";
import Link from "next/link";

import {
  MAP_WIDTH,
  REGIONS,
  type Point,
  project,
} from "@/lib/geo/northAmericaMap";

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
 * The corners the map is cropped to. North of this parallel is arctic and
 * west of this meridian is the Alaskan panhandle and the Aleutians, neither
 * of which carries postings; south of it is open water and the Gulf. The
 * frame still opens up around a pin that lands outside, so cropping can
 * never drop one.
 */
const CROP_NORTH = 54;
const CROP_SOUTH = 24;
const CROP_WEST = -128;

/** Sizes are quoted against this width and scaled with the crop. */
const REFERENCE_WIDTH = 800;
/*
 * Sized against a map that is now wider than it is tall. At the old maximum
 * the leading city drew a circle a fifth of the drawing's height, and the
 * Bay Area cluster covered the names of the cities around it.
 */
const MIN_RADIUS = 10;
const MAX_RADIUS = 28;
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
  const cropNorthWest = project([CROP_WEST, CROP_NORTH]);
  const cropSouth = project([CROP_WEST, CROP_SOUTH]);

  const frame = {
    minX: Math.min(cropNorthWest.x, ...anchors.map((a) => a.x - MARGIN)),
    minY: Math.min(cropNorthWest.y, ...anchors.map((a) => a.y - MARGIN)),
    maxX: Math.max(MAP_WIDTH + MARGIN, ...anchors.map((a) => a.x + MARGIN)),
    maxY: Math.max(cropSouth.y, ...anchors.map((a) => a.y + MARGIN)),
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
      /* Height follows the drawing's own proportions. The Canadian outline
         this replaced was taller than it was wide and filled a card stretched
         by the ranking beside it; North America is nearly twice as wide as it
         is tall, and filling the same card letterboxed it into a thin band
         with half the card empty above and below. */
      className="h-auto w-full"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      style={{ ["--pin-label" as string]: `${labelSize}px` } as CSSProperties}
      aria-label={`Postings by location on a map of the United States and Canada. ${placed
        .map((pin) => `${pin.label}, ${pin.value}`)
        .join(". ")}`}
    >
      {REGIONS.map((region) => (
        <path
          key={region.id}
          d={region.d}
          fill="var(--color-surface-muted)"
          stroke="var(--color-border)"
          strokeWidth={unit}
          strokeLinejoin="round"
        >
          <title>{region.title}</title>
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
          className="group cursor-pointer outline-none [&:focus-visible>circle]:stroke-accent [&:hover>circle]:stroke-accent"
        >
          {pin.labelX !== undefined && pin.labelY !== undefined ? (
            <text
              x={pin.labelX}
              y={pin.labelY}
              textAnchor={pin.anchor}
              /*
               * Crowded pins are hard to tell apart, and two neighbouring
               * cities can carry the same count. Pointing at one grows and
               * darkens its name so it is clear which city was found.
               *
               * The resting size is computed from the map's own scale, so it
               * travels as a custom property the hover rule can multiply
               * rather than a fixed size the rule would have to repeat.
               */
              style={{ fontSize: "var(--label-size)" } as CSSProperties}
              className="transition-[font-size,fill,font-weight] duration-150 [--label-size:var(--pin-label)] [fill:var(--color-text-muted)] group-focus-visible:[--label-size:calc(var(--pin-label)*1.35)] group-focus-visible:font-bold group-focus-visible:[fill:var(--color-text)] group-hover:[--label-size:calc(var(--pin-label)*1.35)] group-hover:font-bold group-hover:[fill:var(--color-text)]"
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
