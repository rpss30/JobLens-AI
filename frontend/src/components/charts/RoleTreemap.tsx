/*
 * A squarified treemap of role categories.
 *
 * Hand-rolled for the same reason as the bubble chart: Recharts has no
 * treemap layout worth using here and the frontend carries no extra chart
 * dependencies. Tiles are HTML rather than SVG so each one can hold an icon,
 * a label, and a percentage pill without hand-positioning text.
 */

export interface TreemapDatum {
  label: string;
  value: number;
}

interface Tile extends TreemapDatum {
  x: number;
  y: number;
  width: number;
  height: number;
  step: number;
}

interface Area extends TreemapDatum {
  area: number;
}

interface Frame {
  x: number;
  y: number;
  width: number;
  height: number;
}

const RAMP_STEPS = 5;

/** Aspect ratio of the worst tile in a row: lower is squarer. */
function worstRatio(row: Area[], side: number): number {
  if (row.length === 0 || side === 0) {
    return Number.POSITIVE_INFINITY;
  }

  const sum = row.reduce((total, item) => total + item.area, 0);

  if (sum === 0) {
    return Number.POSITIVE_INFINITY;
  }

  const largest = Math.max(...row.map((item) => item.area));
  const smallest = Math.min(...row.map((item) => item.area));

  return Math.max(
    (side * side * largest) / (sum * sum),
    (sum * sum) / (side * side * smallest),
  );
}

function squarify(items: Area[], frame: Frame, tiles: Omit<Tile, "step">[]) {
  if (items.length === 0) {
    return;
  }

  const side = Math.min(frame.width, frame.height);
  let row: Area[] = [];
  let index = 0;

  // Grow the row while it keeps getting squarer, then commit it.
  while (index < items.length) {
    const candidate = [...row, items[index]];

    if (row.length > 0 && worstRatio(candidate, side) > worstRatio(row, side)) {
      break;
    }

    row = candidate;
    index += 1;
  }

  const rowArea = row.reduce((total, item) => total + item.area, 0);
  const thickness = side === 0 ? 0 : rowArea / side;
  const isWide = frame.width >= frame.height;
  let offset = 0;

  for (const item of row) {
    const length = thickness === 0 ? 0 : item.area / thickness;

    tiles.push(
      isWide
        ? {
            ...item,
            x: frame.x,
            y: frame.y + offset,
            width: thickness,
            height: length,
          }
        : {
            ...item,
            x: frame.x + offset,
            y: frame.y,
            width: length,
            height: thickness,
          },
    );

    offset += length;
  }

  squarify(
    items.slice(row.length),
    isWide
      ? {
          x: frame.x + thickness,
          y: frame.y,
          width: frame.width - thickness,
          height: frame.height,
        }
      : {
          x: frame.x,
          y: frame.y + thickness,
          width: frame.width,
          height: frame.height - thickness,
        },
    tiles,
  );
}

export function layoutTreemap(data: TreemapDatum[]): Tile[] {
  const ranked = [...data]
    .filter((item) => item.value > 0)
    .sort((first, second) => second.value - first.value);
  const total = ranked.reduce((sum, item) => sum + item.value, 0);

  if (total === 0) {
    return [];
  }

  // Laid out in a 100x100 space so the tiles can be positioned in percentages
  // and the chart resizes with its container.
  const items: Area[] = ranked.map((item) => ({
    ...item,
    area: (item.value / total) * 100 * 100,
  }));
  const tiles: Omit<Tile, "step">[] = [];

  squarify(items, { x: 0, y: 0, width: 100, height: 100 }, tiles);

  return tiles.map((tile, index) => ({
    ...tile,
    step: Math.min(
      RAMP_STEPS,
      1 + Math.floor((index / Math.max(tiles.length, 1)) * RAMP_STEPS),
    ),
  }));
}
