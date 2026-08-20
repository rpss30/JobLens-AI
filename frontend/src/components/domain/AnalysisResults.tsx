"use client";

import Link from "next/link";
import { useState } from "react";

import { JobMatchCard } from "@/components/domain/JobMatchCard";
import { ReportDownloads } from "@/components/domain/ReportDownloads";
import { RoleFitPanel } from "@/components/domain/RoleFitPanel";
import { SaveAnalysisButton } from "@/components/domain/SaveAnalysisButton";
import { SkillGapPanel } from "@/components/domain/SkillGapPanel";
import { Section } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { StatTile } from "@/components/ui/StatTile";
import { EmptyState } from "@/components/ui/States";
import { useAnalysis } from "@/context/AnalysisContext";
import type { JobMatch } from "@/lib/api/types";
import { formatCount, formatPercent, formatSkill } from "@/lib/format";

/** Best fit first, rather than the alphabetical order the data arrives in. */
const EXPERIENCE_FIT_ORDER = ["Meets requirement", "Close match", "Stretch"];

function countBy(jobs: JobMatch[], key: "role_category" | "experience_fit") {
  const counts = new Map<string, number>();

  for (const job of jobs) {
    const value = job[key];

    if (value) {
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
  }

  return counts;
}

function FilterChip({
  label,
  count,
  isSelected,
  isDisabled,
  onSelect,
}: {
  label: string;
  count: number;
  isSelected: boolean;
  isDisabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={isSelected}
      disabled={isDisabled}
      onClick={onSelect}
      className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-45 ${
        isSelected
          ? "border-transparent bg-accent-fill text-on-accent"
          : "border-border bg-surface text-text-muted hover:bg-surface-muted hover:text-text disabled:hover:bg-surface disabled:hover:text-text-muted"
      }`}
    >
      {label}
      <span className="ml-1.5 tabular-nums opacity-70">{count}</span>
    </button>
  );
}

function FilterChipRow({
  label,
  values,
  counts,
  allCount,
  selected,
  onSelect,
}: {
  label: string;
  values: string[];
  counts: Map<string, number>;
  allCount: number;
  selected: string | null;
  onSelect: (value: string | null) => void;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className="flex flex-wrap items-center gap-2"
    >
      <span className="mr-1 text-xs font-medium uppercase tracking-wide text-text-subtle">
        {label}
      </span>
      <FilterChip
        label="All"
        count={allCount}
        isSelected={selected === null}
        isDisabled={false}
        onSelect={() => onSelect(null)}
      />
      {values.map((value) => {
        const count = counts.get(value) ?? 0;

        return (
          <FilterChip
            key={value}
            label={value}
            count={count}
            isSelected={selected === value}
            // Disabled rather than hidden: a zero still says something, and
            // clicking through to an empty list would be a dead end.
            isDisabled={count === 0 && selected !== value}
            onSelect={() => onSelect(value)}
          />
        );
      })}
    </div>
  );
}

/**
 * The result of the last analysis, shown where it was asked for.
 *
 * It used to live on Overview. Overview is the landing page now, so a result
 * stays on Analyze rather than throwing the reader to another tab to read it.
 */
export function AnalysisResults({ datasetName }: { datasetName: string }) {
  const { analysis, clearAnalysis } = useAnalysis();
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [activeFit, setActiveFit] = useState<string | null>(null);
  // The caller decides what stands in for a result that is not there.
  if (!analysis) {
    return null;
  }

  const { response, request } = analysis;

  const allJobs = response.top_matching_jobs;

  /*
   * Both filters come from the matches themselves rather than fixed lists, so
   * neither row can offer a value with no jobs behind it.
   */
  const categories = [...countBy(allJobs, "role_category").keys()].sort();
  const fits = [...countBy(allJobs, "experience_fit").keys()].sort(
    (first, second) =>
      EXPERIENCE_FIT_ORDER.indexOf(first) -
      EXPERIENCE_FIT_ORDER.indexOf(second),
  );

  /*
   * A new analysis can drop whatever was selected. Falling back to all matches
   * beats showing an empty list, and needs no effect to reset.
   */
  const selectedCategory =
    activeCategory && categories.includes(activeCategory)
      ? activeCategory
      : null;
  const selectedFit = activeFit && fits.includes(activeFit) ? activeFit : null;

  const matchesCategory = (job: JobMatch) =>
    !selectedCategory || job.role_category === selectedCategory;
  const matchesFit = (job: JobMatch) =>
    !selectedFit || job.experience_fit === selectedFit;

  /*
   * Each row counts against the other filter, so a number always describes
   * what you would actually get by clicking it.
   */
  const categoryCounts = countBy(allJobs.filter(matchesFit), "role_category");
  const fitCounts = countBy(allJobs.filter(matchesCategory), "experience_fit");

  const matchedJobs = allJobs.filter(
    (job) => matchesCategory(job) && matchesFit(job),
  );

  const visibleJobs = matchedJobs.slice(0, 6);
  const remainingJobs = matchedJobs.slice(6);

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Your best role"
          value={response.best_role}
          hint={`Compared against ${formatCount(response.jobs_analyzed)} jobs`}
        />
        <StatTile
          label="Skill match"
          value={formatPercent(response.weighted_match_score)}
          hint="How much of what this role asks for you already have"
          emphasis
        />
        <StatTile
          label="Biggest gap"
          value={formatSkill(response.top_missing_skill)}
          hint="The most in-demand skill you are missing"
        />
        <StatTile
          label="Skills you have"
          value={formatCount(
            response.resume_analysis?.combined_skills.length ??
              request.current_skills.length,
          )}
          hint={
            response.resume_analysis
              ? "Including skills found in your resume"
              : undefined
          }
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <SaveAnalysisButton />
        <ReportDownloads />
        {/* Puts the form back where the result is, rather than sending the
            reader off to find it. */}
        <button
          type="button"
          onClick={clearAnalysis}
          className="text-sm font-medium text-accent hover:underline"
        >
          Run a new analysis
        </button>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <RoleFitPanel roleScores={response.role_scores} />
        <SkillGapPanel skills={response.recommended_skills} />
      </div>

      <Section
        title="Jobs worth applying to first"
        description="These openings ask for the most skills you already have."
        action={
          <Link
            href={`/jobs?dataset=${encodeURIComponent(datasetName)}`}
            className="text-sm font-medium text-accent hover:underline"
          >
            Browse all postings
          </Link>
        }
      >
        {categories.length > 1 || fits.length > 1 ? (
          <div className="mb-5 space-y-2.5">
            {categories.length > 1 ? (
              <FilterChipRow
                label="Category"
                values={categories}
                counts={categoryCounts}
                allCount={allJobs.filter(matchesFit).length}
                selected={selectedCategory}
                onSelect={setActiveCategory}
              />
            ) : null}
            {fits.length > 1 ? (
              <FilterChipRow
                label="Experience fit"
                values={fits}
                counts={fitCounts}
                allCount={allJobs.filter(matchesCategory).length}
                selected={selectedFit}
                onSelect={setActiveFit}
              />
            ) : null}
          </div>
        ) : null}

        {visibleJobs.length === 0 ? (
          <EmptyState
            title="No close matches yet"
            description="None of these jobs overlap with the skills you listed. Try adding more skills, or widening your search."
            action={
              <Button variant="secondary" onClick={clearAnalysis}>
                Change my search
              </Button>
            }
          />
        ) : (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {/* Title and company are not unique: one employer can post the
                  same role twice, which collided as a React key. */}
              {visibleJobs.map((job, index) => (
                <JobMatchCard
                  key={`${job.title}-${job.company}-${index}`}
                  job={job}
                />
              ))}
            </div>

            {remainingJobs.length > 0 ? (
              <details className="group">
                <summary className="inline-flex cursor-pointer list-none items-center rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-surface-muted">
                  Show more matches ({remainingJobs.length})
                </summary>
                <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {remainingJobs.map((job, index) => (
                    <JobMatchCard
                      key={`${job.title}-${job.company}-${visibleJobs.length + index}`}
                      job={job}
                    />
                  ))}
                </div>
              </details>
            ) : null}
          </div>
        )}
      </Section>

      {response.resume_analysis ? (
        <Section
          title="Resume analysis"
          description={response.resume_analysis.privacy_note}
        >
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-sm text-text">
              {response.resume_analysis.explanation}
            </p>
            {response.resume_analysis.resume_skills.length > 0 ? (
              <ul className="mt-4 flex flex-wrap gap-1.5">
                {response.resume_analysis.resume_skills
                  .slice(0, 18)
                  .map((skill) => (
                    <li key={skill}>
                      <Badge tone="accent">{formatSkill(skill)}</Badge>
                    </li>
                  ))}
              </ul>
            ) : null}
          </div>
        </Section>
      ) : null}
    </div>
  );
}
