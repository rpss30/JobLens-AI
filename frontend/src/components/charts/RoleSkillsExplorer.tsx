"use client";

import { useEffect, useRef, useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

import { CategoryIcon } from "@/components/charts/CategoryIcons";
import {
  REQUIREMENT_SIGNAL,
  RequirementLegend,
} from "@/components/charts/RequirementSignal";
import { Card, CardBody } from "@/components/ui/Card";
import { Field, controlClassName } from "@/components/ui/Field";
import type { RoleSkillImportance } from "@/lib/api/types";
import { formatCount, formatSkill } from "@/lib/format";

const DEMAND_LABEL: Record<RoleSkillImportance["demand_signal"], string> = {
  leading: "Leading signal",
  common: "Common signal",
  specialized: "Specialized signal",
};

export interface RoleGroup {
  roleCategory: string;
  rolePostings: number;
  skills: RoleSkillImportance[];
}

function shareOf(skill: RoleSkillImportance): number {
  return skill.role_job_count > 0 ? skill.job_count / skill.role_job_count : 0;
}

/** Skill name above its share, so the chart reads without a legend. */
interface AxisTickProps {
  // Recharts hands ticks a wide prop type, so the few fields used here are
  // picked out rather than the whole shape being asserted away.
  payload?: { value?: string };
  x?: string | number;
  y?: string | number;
  cx?: string | number;
  cy?: string | number;
  textAnchor?: string;
}

const LABEL_FONT_SIZE = 12;
const HOVERED_FONT_SIZE = 15;
/** Breathing room between a label and the edge of the drawing. */
const EDGE_PADDING = 8;

let measureContext: CanvasRenderingContext2D | null = null;
let measureFont = "";

/**
 * How wide the browser will actually draw a string.
 *
 * A character count cannot answer this: in a proportional face "Kubernetes"
 * and "IIIIIIIIII" are the same length and nothing like the same width, which
 * is why counting characters either clipped long labels or cut short ones
 * that had room to spare.
 *
 * Only ever runs in the browser. Recharts' ResponsiveContainer draws nothing
 * until it has measured itself, so no tick is rendered on the server.
 */
export function textWidth(text: string, fontSize: number, fontWeight: number): number {
  measureContext ??= document.createElement("canvas").getContext("2d");

  if (!measureContext) {
    // No canvas: guess generously, so labels come out short rather than
    // overflowing the chart.
    return text.length * fontSize * 0.62;
  }

  measureFont ||= getComputedStyle(document.body).fontFamily || "sans-serif";
  measureContext.font = `${fontWeight} ${fontSize}px ${measureFont}`;

  return measureContext.measureText(text).width;
}

/**
 * Trim a label to the room it has, ending in an ellipsis.
 *
 * Binary search over the string, so the cost is a handful of measurements
 * whatever the length, and any string can be handled rather than the few
 * lengths a lookup table would cover.
 */
export function fitLabel(
  label: string,
  available: number,
  fontSize: number,
  fontWeight: number,
): string {
  if (textWidth(label, fontSize, fontWeight) <= available) {
    return label;
  }

  let fits = 0;
  let tooLong = label.length;

  while (fits < tooLong) {
    const middle = Math.ceil((fits + tooLong) / 2);
    const candidate = `${label.slice(0, middle).trimEnd()}…`;

    if (textWidth(candidate, fontSize, fontWeight) <= available) {
      fits = middle;
    } else {
      tooLong = middle - 1;
    }
  }

  // Even one character and an ellipsis can be too wide; the tooltip still
  // carries the full name.
  return fits > 0 ? `${label.slice(0, fits).trimEnd()}…` : "…";
}

/** The room a label has between where it is anchored and the nearest edge. */
function roomForLabel(
  labelX: number,
  textAnchor: string | undefined,
  chartWidth: number,
): number {
  if (textAnchor === "start") {
    return chartWidth - EDGE_PADDING - labelX;
  }

  if (textAnchor === "end") {
    return labelX - EDGE_PADDING;
  }

  // Centred labels grow both ways, so the tighter side decides.
  return (
    2 * Math.min(labelX - EDGE_PADDING, chartWidth - EDGE_PADDING - labelX)
  );
}

function renderAxisTick(
  { payload, x, y, cx, cy, textAnchor }: AxisTickProps,
  shares: Map<string, number>,
  hoveredSkill: string | null,
) {
  const label = payload?.value ?? "";
  const isHovered = label === hoveredSkill;

  const tickX = Number(x ?? 0);
  const tickY = Number(y ?? 0);
  const centerX = Number(cx ?? tickX);
  const centerY = Number(cy ?? tickY);

  const dx = tickX - centerX;
  const dy = tickY - centerY;
  const distance = Math.sqrt(dx * dx + dy * dy) || 1;

  /*
   * Taken from the centre Recharts hands this tick rather than from a width
   * observed alongside the chart. An observed width is a frame behind during
   * a resize, and labels laid out against the previous width overhang the
   * edge of the new one.
   */
  const chartWidth = centerX * 2;

  const isCompact = chartWidth > 0 && chartWidth < 560;

  /*
   * Top/bottom labels have lots of horizontal room, so they can sit farther
   * from the radar. Side labels have less room and stay closer to the tips.
   */
  const isVerticalAxis = Math.abs(dy) > Math.abs(dx) * 1.5;
  const isTop = isVerticalAxis && dy < 0;
  const isBottom = isVerticalAxis && dy > 0;

  let offset: number;

  if (isTop) {
    // Deliberately farther away so Python/etc. does not collide with 100%.
    offset = isCompact ? 36 : 34;
  } else if (isBottom) {
    offset = isCompact ? 28 : 30;
  } else {
    // Pull side labels inward on narrow charts.
    offset = isCompact ? 10 : 30;
  }

  let labelX = tickX + (dx / distance) * offset;
  const labelY = tickY + (dy / distance) * offset;

  // An anchor outside the drawing leaves a label nowhere to go, so pull it
  // back to the edge before working out what will fit.
  if (chartWidth > 0) {
    labelX = Math.min(Math.max(labelX, EDGE_PADDING), chartWidth - EDGE_PADDING);
  }

  /*
   * Measured at the hovered size even when it is not hovered. Highlighting a
   * point grows its label, and a label sized to fit at 12px would spill over
   * the edge the moment it became 15px.
   */
  const displayLabel =
    chartWidth > 0
      ? fitLabel(
          label,
          roomForLabel(labelX, textAnchor, chartWidth),
          HOVERED_FONT_SIZE,
          700,
        )
      : label;
  const isTruncated = displayLabel !== label;

  return (
    <text
      x={labelX}
      y={labelY}
      textAnchor={textAnchor as "start" | "middle" | "end" | undefined}
      dominantBaseline="middle"
    >
      {isTruncated ? <title>{label}</title> : null}

      <tspan
        x={labelX}
        dy="-0.3em"
        fill="var(--color-text)"
        fontSize={isHovered ? HOVERED_FONT_SIZE : LABEL_FONT_SIZE}
        fontWeight={isHovered ? 700 : 500}
      >
        {displayLabel}
      </tspan>

      <tspan
        x={labelX}
        dy="1.3em"
        fill="var(--color-accent)"
        fontSize={isHovered ? HOVERED_FONT_SIZE : LABEL_FONT_SIZE}
        fontWeight={isHovered ? 700 : 600}
      >
        {Math.round((shares.get(label) ?? 0) * 100)}%
      </tspan>
    </text>
  );
}

interface RadarDotProps {
  cx?: number;
  cy?: number;
  payload?: { label?: string };
}

export function RoleSkillsExplorer({ roles }: { roles: RoleGroup[] }) {
  const [selectedRole, setSelectedRole] = useState(
    roles[0]?.roleCategory ?? "",
  );
  const [hoveredSkill, setHoveredSkill] = useState<string | null>(null);

  const radarContainerRef = useRef<HTMLDivElement | null>(null);
  const [radarWidth, setRadarWidth] = useState(0);

  useEffect(() => {
    const element = radarContainerRef.current;

    if (!element) {
      return;
    }

    const observer = new ResizeObserver(([entry]) => {
      setRadarWidth(entry.contentRect.width);
    });

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, []);

  const selected =
    roles.find((role) => role.roleCategory === selectedRole) ?? roles[0];

  if (!selected) {
    return null;
  }

  const radarData = selected.skills.map((skill) => ({
    label: formatSkill(skill.skill),
    value: Math.round(shareOf(skill) * 100),
  }));
  const shares = new Map(
    selected.skills.map((skill) => [formatSkill(skill.skill), shareOf(skill)]),
  );

  return (
    <div className="grid gap-5 xl:grid-cols-2">
      {/*
       * Narrow screens get one role at a time, picked here. The grid of cards
       * below needs room to be worth reading: stacked into a single column it
       * became a list to scroll past rather than a choice to make.
       */}
      <div className="xl:hidden">
        <Field label="Role category" htmlFor="role-category">
          <select
            id="role-category"
            value={selected.roleCategory}
            onChange={(event) => setSelectedRole(event.target.value)}
            className={controlClassName}
          >
            {roles.map((role) => (
              <option key={role.roleCategory} value={role.roleCategory}>
                {role.roleCategory} &mdash; {formatCount(role.rolePostings)}{" "}
                postings
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="hidden xl:grid xl:h-full xl:auto-rows-fr xl:grid-cols-2 xl:gap-4">
        {roles.map((role) => {
          const isSelected = role.roleCategory === selected.roleCategory;

          return (
            <button
              key={role.roleCategory}
              type="button"
              aria-pressed={isSelected}
              onClick={() => setSelectedRole(role.roleCategory)}
              className={`flex h-full flex-col rounded-xl border bg-surface p-4 text-left transition-colors ${
                isSelected
                  ? "border-accent ring-1 ring-accent"
                  : "border-border hover:bg-surface-muted"
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex rounded-xl bg-accent-soft p-2.5 text-accent">
                  <CategoryIcon category={role.roleCategory} />
                </span>
                <div className="min-w-0">
                  <p className="truncate text-base font-medium text-text">
                    {role.roleCategory}
                  </p>
                  <p className="text-xs text-text-subtle">
                    {formatCount(role.rolePostings)} postings
                  </p>
                </div>
              </div>

              <div className="mt-3 flex items-baseline justify-between gap-2 text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle">
                <span>Top skills</span>
                <span>Share of postings</span>
              </div>

              <ul className="mt-1.5 space-y-1.5">
                {role.skills.slice(0, 3).map((skill, index) => (
                  <li
                    key={skill.skill}
                    className="flex items-center gap-2 rounded-lg bg-surface-muted px-2.5 py-1.5"
                  >
                    <span className="w-4 shrink-0 text-xs tabular-nums text-text-subtle">
                      {index + 1}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm text-text">
                      {formatSkill(skill.skill)}
                    </span>
                    <span className="shrink-0 text-sm tabular-nums text-text-muted">
                      {Math.round(shareOf(skill) * 100)}%
                    </span>
                  </li>
                ))}
              </ul>

              <span className="mt-auto inline-flex items-center gap-1 pt-3 text-sm font-medium text-accent">
                {isSelected ? "Showing details" : "View details"}
                <span aria-hidden="true">→</span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="min-w-0">
        <Card className="flex flex-col">
          {/* One card, split by a rule: the key and the tags it explains belong
              to the same surface rather than floating apart.
              On a narrow screen the key moves below the chart. Above it, four
              rows of key stood between the dropdown and the thing the reader
              opened the page for. The rule follows it to whichever edge it
              ends up against. */}
          <div className="order-last border-t border-border p-5 xl:order-none xl:border-b xl:border-t-0">
            <RequirementLegend />
          </div>

          {/* Keyed on the role: React swaps the subtree, which restarts the
              animation so the change reads as a move between roles. */}
          <CardBody key={selected.roleCategory} className="animate-panel-in p-5">
            <div className="flex items-center gap-3">
              <span className="inline-flex rounded-xl bg-accent-soft p-2.5 text-accent">
                <CategoryIcon category={selected.roleCategory} />
              </span>
              <div className="min-w-0">
                <h2 className="truncate text-xl font-medium text-text">
                  {selected.roleCategory}
                </h2>
                <p className="text-sm text-text-muted">
                  {formatCount(selected.rolePostings)} postings
                </p>
              </div>
            </div>

            <p className="mt-3 text-sm text-text-muted">
              Skills ranked against the others in this role. Each figure is the
              share of this role&rsquo;s postings that ask for the skill.
            </p>

            {/* Three points is the minimum that makes a shape rather than a line. */}
            {radarData.length >= 3 ? (
              <div
                ref={radarContainerRef}
                className="mt-4 h-[22rem]"
              >
                {/* The axis stays 0-100 so a role with modest shares looks
                    modest. Scaling to each role's own maximum would make every
                    profile look equally strong.

                    The chart is ResponsiveContainer's only child on purpose: it
                    clones that child to hand it the measured size, and anything
                    beside it left the chart on its 500px default width, which
                    then overflowed the card and cut the labels off. */}
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart
                    data={radarData}
                    outerRadius={radarWidth > 0 && radarWidth < 560 ? "54%" : "58%"}
                  >
                    <PolarGrid stroke="var(--color-border)" />
                    <PolarAngleAxis
                      dataKey="label"
                      tick={(props: AxisTickProps) =>
                        renderAxisTick(props, shares, hoveredSkill)
                      }
                    />
                    <PolarRadiusAxis
                      type="number"
                      angle={90}
                      domain={[0, 100]}
                      tickCount={5}
                      tick={{ fill: "var(--color-text-subtle)", fontSize: 10 }}
                      tickFormatter={(value: number) => `${value}%`}
                    />
                    <Radar
                      dataKey="value"
                      stroke="var(--color-chart-2)"
                      fill="var(--color-chart-2)"
                      fillOpacity={0.22}
                      isAnimationActive={false}
                      // Drawn by hand so each point can say which skill it is
                      // and grow its label while the pointer is on it.
                      dot={(props: RadarDotProps) => {
                        const label = props.payload?.label ?? "";
                        const isHovered = label === hoveredSkill;

                        return (
                          <circle
                            key={label}
                            cx={props.cx}
                            cy={props.cy}
                            r={isHovered ? 6.5 : 4}
                            fill="var(--color-chart-2)"
                            stroke="var(--color-surface)"
                            strokeWidth={1.5}
                            onMouseEnter={() => setHoveredSkill(label)}
                            onMouseLeave={() => setHoveredSkill(null)}
                          />
                        );
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            ) : null}

            <ul className="mt-4 grid gap-x-5 gap-y-2 sm:grid-cols-2">
              {selected.skills.map((skill) => {
                const requirement = REQUIREMENT_SIGNAL[skill.requirement_signal];

                return (
                  <li
                    key={skill.skill}
                    className="flex items-center gap-2.5"
                    title={`${requirement.label}. ${requirement.hint}. ${DEMAND_LABEL[skill.demand_signal]}.`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-text">
                        {formatSkill(skill.skill)}
                        {/* Colour alone should not carry the meaning. */}
                        <span className="sr-only">
                          {" "}
                          &mdash; {requirement.label}
                        </span>
                      </p>
                      <span className="mt-1 block h-1.5 rounded-full bg-surface-muted">
                        <span
                          className="block h-1.5 rounded-full"
                          style={{
                            width: `${Math.max(shareOf(skill) * 100, 3)}%`,
                            backgroundColor: requirement.color,
                          }}
                        />
                      </span>
                    </div>
                    <span className="w-9 shrink-0 text-right text-xs tabular-nums text-text-muted">
                      {Math.round(shareOf(skill) * 100)}%
                    </span>
                  </li>
                );
              })}
            </ul>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
