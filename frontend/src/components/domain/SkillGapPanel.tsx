"use client";

import Link from "next/link";
import { useState } from "react";

import { CategoryIcon } from "@/components/charts/CategoryIcons";
import { SkillBubbleChart } from "@/components/charts/SkillBubbleChart";
import { Card } from "@/components/ui/Card";
import { SingleSelectCombobox } from "@/components/ui/SingleSelectCombobox";
import type { RecommendedSkill, RoleRecommendedSkills } from "@/lib/api/types";
import { formatCount, formatSkill } from "@/lib/format";

/*
 * The tallest bar stops short of the top so the figure above it has somewhere
 * to sit. Without this the leading skill's count would ride out of the chart.
 */
const MAX_BAR_HEIGHT = 84;

/*
 * Only where the full name is too long to sit in a row of tabs. Everything
 * else is named the way the rest of the app names it.
 */
const TAB_LABELS: Record<string, string> = {
  "Software Engineering": "SWE",
};

function SkillBars({ skills }: { skills: RecommendedSkill[] }) {
  const mostAskedFor = Math.max(...skills.map((skill) => skill.job_count), 1);

  return (
    // Ten skills need more width than a narrow screen has, so the chart
    // scrolls inside its own box rather than squeezing the labels.
    <div className="overflow-x-auto">
      <div className="min-w-[38rem]">
        <ul className="flex h-56 items-end gap-2 border-b border-border-strong">
          {skills.map((skill, index) => (
            <li
              key={skill.skill}
              // A band behind the column rather than a taller bar: the height
              // is the value, so nothing that reads as the value moves.
              title={`${formatSkill(skill.skill)}: ${formatCount(skill.job_count)} ${
                skill.job_count === 1 ? "job" : "jobs"
              }`}
              className="group flex h-full flex-1 flex-col items-center justify-end rounded-t-lg transition-colors hover:bg-surface-muted"
            >
              <p className="mb-1.5 text-sm font-semibold tabular-nums text-text transition-colors group-hover:text-accent">
                {formatCount(skill.job_count)}
              </p>
              <div
                style={{
                  height: `${(skill.job_count / mostAskedFor) * MAX_BAR_HEIGHT}%`,
                  // Left to right, so the chart reads in the order it ranks.
                  animationDelay: `${index * 45}ms`,
                }}
                className="animate-bar-grow w-full max-w-9 bg-chart-mark ring-chart-mark/35 transition-[box-shadow] group-hover:ring-4"
              />
            </li>
          ))}
        </ul>

        <ul className="flex gap-2 pt-3">
          {skills.map((skill) => (
            <li
              key={skill.skill}
              className="flex-1 text-center text-xs leading-snug text-text-muted"
            >
              {formatSkill(skill.skill)}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function SkillGapPanel({
  skills,
  byRole,
  datasetName,
}: {
  skills: RecommendedSkill[];
  byRole: RoleRecommendedSkills[];
  datasetName: string;
}) {
  const [activeRole, setActiveRole] = useState<string | null>(null);

  /*
   * A category with nothing missing has no tab: an empty chart behind a name
   * says less than not offering the name at all.
   */
  const tabs = byRole.filter((entry) => entry.skills.length > 0);

  const selected =
    tabs.find((entry) => entry.role_category === activeRole) ?? tabs[0];
  // Every posting in the analysis, for a result whose categories never came
  // back. The ranking is the same calculation, run over all of them at once.
  const rows = selected ? selected.skills : skills;

  return (
    <Card className="px-5 py-5 sm:px-6 sm:py-6">
      {/* One grid so the link can sit beside the description from md and at
          the foot of the card below it, without being written out twice. */}
      <div className="grid gap-x-6 gap-y-5 md:grid-cols-[minmax(0,1fr)_auto]">
        <p className="text-sm text-text-muted md:col-start-1 md:row-start-1">
          Prioritize the missing skills that appear most often in jobs
          you&rsquo;re targeting
        </p>

        {/* A row of pills needs width a phone has not got, so below md the
            same choice is a dropdown with the sample size beside it. */}
        {tabs.length > 1 && selected ? (
          <div className="flex items-center gap-3 md:hidden md:col-span-2 md:row-start-2">
            <div className="min-w-0 flex-1">
              <SingleSelectCombobox
                id="skill-role"
                size="compact"
                placeholder="All roles"
                value={selected.role_category}
                onChange={setActiveRole}
                // Inside the control rather than beside it: the mark belongs
                // to the category it names, not to the row.
                leading={<CategoryIcon category={selected.role_category} />}
                options={tabs.map((entry) => ({
                  value: entry.role_category,
                  label: entry.role_category,
                }))}
              />
            </div>
            <span className="shrink-0 text-sm tabular-nums text-text-subtle">
              {formatCount(selected.job_count)}{" "}
              {selected.job_count === 1 ? "job" : "jobs"}
            </span>
          </div>
        ) : null}

        {tabs.length > 1 ? (
          <div
            role="tablist"
            aria-label="Role category"
            className="hidden flex-wrap gap-2 md:col-span-2 md:row-start-2 md:flex"
          >
            {tabs.map((entry) => {
              const isSelected =
                entry.role_category === selected?.role_category;

              return (
                <button
                  key={entry.role_category}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  onClick={() => setActiveRole(entry.role_category)}
                  title={entry.role_category}
                  className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm transition-colors ${
                    isSelected
                      ? "border-transparent bg-accent-fill text-on-accent"
                      : "border-border bg-surface text-text hover:bg-surface-muted"
                  }`}
                >
                  {/* The same mark Market Insights gives this category, so a
                      role is recognised the same way everywhere. */}
                  <span className="shrink-0">
                    <CategoryIcon category={entry.role_category} />
                  </span>
                  <span className="font-medium">
                    {TAB_LABELS[entry.role_category] ?? entry.role_category}
                  </span>
                  {/* How many postings the ranking behind the tab is drawn
                    from, so a short list reads as a small sample. */}
                  <span
                    className={`ml-2 tabular-nums ${
                      isSelected ? "opacity-70" : "text-text-subtle"
                    }`}
                  >
                    {formatCount(entry.job_count)}{" "}
                    {entry.job_count === 1 ? "job" : "jobs"}
                  </span>
                </button>
              );
            })}
          </div>
        ) : null}

        {rows.length === 0 ? (
          <p className="py-6 text-sm text-text-muted md:col-span-2 md:row-start-3">
            Nothing major is missing for this search.
          </p>
        ) : (
          <div className="md:col-span-2 md:row-start-3">
            <p className="text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle">
              Jobs asking for it
            </p>
            <div className="mt-2 border-t border-border pt-8">
              {/* Ten bars need a width a phone has not got, and shrinking them
                takes the labels with it. Packed circles carry the same one
                series in a square, which is the shape a phone has. */}
              <div className="md:hidden">
                <SkillBubbleChart
                  data={rows.map((skill) => ({
                    label: formatSkill(skill.skill),
                    value: skill.job_count,
                  }))}
                  valueLabel="jobs asking for it"
                />
              </div>
              <div className="hidden md:block">
                <SkillBars skills={rows} />
              </div>
            </div>
          </div>
        )}

        <Link
          href={`/skills?dataset=${encodeURIComponent(datasetName)}`}
          // The page this leads to arrives behind a Suspense boundary, so it
          // commits before there is content to scroll and the reader lands
          // part way down a page they have not seen the top of.
          onClick={() => window.scrollTo({ top: 0 })}
          className="inline-flex items-center gap-2 text-sm font-medium text-accent hover:underline md:col-start-2 md:row-start-1 md:justify-self-end"
        >
          View all skills
          <span aria-hidden="true">&rarr;</span>
        </Link>
      </div>
    </Card>
  );
}
