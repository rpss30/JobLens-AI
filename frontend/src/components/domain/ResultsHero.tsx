"use client";

import { CountUp } from "@/components/ui/CountUp";
import type { AnalyzeResponse } from "@/lib/api/types";
import {
  formatCount,
  formatDatasetLabel,
  formatPercent,
  formatSkill,
} from "@/lib/format";

/**
 * One figure and what it is.
 *
 * The label sits under the value rather than over it, so the three read as a
 * row of answers to the heading beside them.
 */
function HeroStat({
  value,
  label,
}: {
  value: React.ReactNode;
  label: string;
}) {
  return (
    <div className="min-w-0">
      <p className="text-3xl font-semibold leading-tight sm:text-[2.25rem]">
        {value}
      </p>
      <p className="mt-2 text-xs">{label}</p>
    </div>
  );
}

/**
 * What the analysis found, in one line: the role that fits best and the three
 * figures worth knowing before reading anything else.
 *
 * It replaced four separate tiles. The role is the finding, and giving it the
 * width of the page says so in a way four equal boxes could not.
 */
export function ResultsHero({
  response,
  skillCount,
}: {
  response: AnalyzeResponse;
  /** Everything the analysis was run against, resume skills included. */
  skillCount: number;
}) {
  return (
    <section className="rounded-2xl bg-hero px-6 py-7 text-on-hero sm:px-9 sm:py-9">
      <p className="text-xs font-medium uppercase tracking-wide">
        {formatDatasetLabel(response.dataset_name)},{" "}
        {formatCount(response.jobs_analyzed)} postings analyzed
      </p>

      <div className="mt-5 flex flex-wrap items-end justify-between gap-x-10 gap-y-7">
        <h2 className="max-w-md text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
          {response.best_role}
        </h2>

        <div className="flex flex-wrap items-end gap-x-10 gap-y-7 sm:gap-x-14">
          <HeroStat
            value={
              <CountUp
                value={response.weighted_match_score}
                decimals={1}
                format={formatPercent}
              />
            }
            label="SKILL MATCH"
          />
          <HeroStat
            value={<CountUp value={skillCount} />}
            label="SKILLS YOU HAVE"
          />
          {/* Not a number, so nothing to count: the gap is a skill's name. */}
          <HeroStat
            value={
              <span className="block max-w-[10ch]">
                {formatSkill(response.top_missing_skill)}
              </span>
            }
            label="BIGGEST GAP"
          />
        </div>
      </div>
    </section>
  );
}
