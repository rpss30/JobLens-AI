"use client";

import { useState } from "react";
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

  // Push every label farther away from the outer tip of the radar.
  const LABEL_OFFSET = 30;

  const dx = tickX - centerX;
  const dy = tickY - centerY;
  const distance = Math.sqrt(dx * dx + dy * dy) || 1;

  const labelX = tickX + (dx / distance) * LABEL_OFFSET;
  const labelY = tickY + (dy / distance) * LABEL_OFFSET;

  return (
    <text
      x={labelX}
      y={labelY}
      textAnchor={textAnchor as "start" | "middle" | "end" | undefined}
      dominantBaseline="middle"
    >
      <tspan
        x={labelX}
        dy="-0.3em"
        fill="var(--color-text)"
        fontSize={isHovered ? 15 : 12}
        fontWeight={isHovered ? 700 : 500}
      >
        {label}
      </tspan>

      <tspan
        x={labelX}
        dy="1.3em"
        fill="var(--color-accent)"
        fontSize={isHovered ? 15 : 12}
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
      <div className="grid h-full auto-rows-fr gap-4 sm:grid-cols-2">
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

      <Card>
        {/* One card, split by a rule: the key and the tags it explains belong
            to the same surface rather than floating apart. */}
        <div className="border-b border-border p-5">
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
            <div className="mt-4 h-[22rem]">
              <ResponsiveContainer width="100%" height="100%">
                {/* The axis stays 0-100 so a role with modest shares looks modest.
                      Scaling to each role's own maximum would make every profile
                      look equally strong. */}
                <RadarChart data={radarData} outerRadius="58%">
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
  );
}
