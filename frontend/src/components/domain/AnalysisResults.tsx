"use client";

import { useState } from "react";

import { JobSortMenu } from "@/components/domain/JobSortMenu";
import { MatchFilters } from "@/components/domain/MatchFilters";
import { MatchResults } from "@/components/domain/MatchResults";
import { ResultsActions } from "@/components/domain/ResultsActions";
import { ResultsHero } from "@/components/domain/ResultsHero";
import { RoleFitPanel } from "@/components/domain/RoleFitPanel";
import { SkillGapPanel } from "@/components/domain/SkillGapPanel";
import { Section } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/States";
import { useAnalysis } from "@/context/AnalysisContext";
import { formatSkill } from "@/lib/format";
import {
  EMPTY_MATCH_FILTERS,
  MATCH_SORT_LABELS,
  activeMatchFilterCount,
  defaultMatchFilters,
  filterMatches,
  matchFilterOptions,
  sortMatches,
  type MatchFilterValues,
  type MatchSortKey,
} from "@/lib/matches";

/*
 * How far apart the sections arrive. Enough to read as one after another,
 * short enough that the last is in before anyone has finished the first.
 */
const SECTION_STAGGER_MS = 90;

const SORT_KEYS: MatchSortKey[] = [
  "match_score",
  "date_posted",
  "title",
  "company",
  "location",
];

function SlidersIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path d="M4 7h10M18 7h2M4 12h4M12 12h8M4 17h10M18 17h2" />
      <circle cx="16" cy="7" r="1.9" />
      <circle cx="10" cy="12" r="1.9" />
      <circle cx="16" cy="17" r="1.9" />
    </svg>
  );
}

/**
 * The result of the last analysis, shown where it was asked for.
 *
 * It used to live on Overview. Overview is the landing page now, so a result
 * stays on Analyze rather than throwing the reader to another tab to read it.
 */
export function AnalysisResults({
  datasetName,
  savedJobIds,
}: {
  datasetName: string;
  /** Which of these postings are already kept, read once on the server. */
  savedJobIds: string[];
}) {
  const { analysis, clearAnalysis } = useAnalysis();
  // Narrowed to the role the analysis settled on, rather than opening on
  // every category it happened to match.
  const [filters, setFilters] = useState<MatchFilterValues>(() =>
    defaultMatchFilters(
      analysis?.response.top_matching_jobs ?? [],
      analysis?.response.best_role ?? "",
    ),
  );
  const [sortKey, setSortKey] = useState<MatchSortKey>("match_score");
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);

  // The caller decides what stands in for a result that is not there.
  if (!analysis) {
    return null;
  }

  const { response, request } = analysis;

  const allJobs = response.top_matching_jobs;

  const filterOptions = matchFilterOptions(allJobs);
  const matchedJobs = sortMatches(filterMatches(allJobs, filters), sortKey);

  // Nothing in this dataset records when a posting went up, so the order
  // would be the one it arrived in under another name.
  const sortKeys = allJobs.some((job) => job.date_posted)
    ? SORT_KEYS
    : SORT_KEYS.filter((key) => key !== "date_posted");

  const activeFilterCount = activeMatchFilterCount(filters);

  return (
    <div className="space-y-10">
      {/* The banner and what can be done with it are one block: the actions
          are about the result under them, not about the page. */}
      <div className="relative z-20 animate-section-in space-y-6">
        <ResultsHero
          response={response}
          skillCount={
            response.resume_analysis?.combined_skills.length ??
            request.current_skills.length
          }
        />
        <ResultsActions />
      </div>

      <div
        className="animate-section-in"
        style={{ animationDelay: `${SECTION_STAGGER_MS}ms` }}
      >
        <Section
          title="Matched Jobs"
          description="These openings ask for the most skills you already have."
          headingSize="large"
          action={
            <div className="flex items-center gap-3">
              <JobSortMenu
                value={sortKey}
                onSelect={(value) => setSortKey(value as MatchSortKey)}
                options={sortKeys.map((key) => ({
                  value: key,
                  label: MATCH_SORT_LABELS[key],
                }))}
              />
              <button
                type="button"
                aria-expanded={isFiltersOpen}
                aria-label={isFiltersOpen ? "Hide filters" : "Show filters"}
                onClick={() => setIsFiltersOpen(!isFiltersOpen)}
                // Square, and the same height as the sort control beside it.
                // Carries the accent while the panel is open, the way every
                // other control here shows that it is the one doing something.
                className={`relative inline-flex size-[2.375rem] shrink-0 items-center justify-center rounded-lg border transition-colors ${
                  isFiltersOpen
                    ? "border-transparent bg-accent-fill text-on-accent hover:bg-accent-fill-hover"
                    : "border-border bg-surface text-text hover:bg-surface-muted"
                }`}
              >
                <SlidersIcon />
                {/* Only worth counting while the panel is shut: open, the
                  filters speak for themselves. */}
                {!isFiltersOpen && activeFilterCount > 0 ? (
                  <span className="absolute -right-1.5 -top-1.5 min-w-[1.125rem] rounded-full bg-accent-fill px-1 text-center text-[0.6875rem] font-medium leading-[1.125rem] text-on-accent">
                    {activeFilterCount}
                  </span>
                ) : null}
              </button>
            </div>
          }
        >
          {matchedJobs.length === 0 ? (
            <EmptyState
              title={
                activeFilterCount > 0
                  ? "No matches with these filters"
                  : "No close matches yet"
              }
              description={
                activeFilterCount > 0
                  ? "Nothing here matches every filter at once. Clear one and try again."
                  : "None of these jobs overlap with the skills you listed. Try adding more skills, or widening your search."
              }
              action={
                activeFilterCount > 0 ? (
                  <Button
                    variant="secondary"
                    onClick={() => setFilters(EMPTY_MATCH_FILTERS)}
                  >
                    Clear filters
                  </Button>
                ) : (
                  <Button variant="secondary" onClick={clearAnalysis}>
                    Change my search
                  </Button>
                )
              }
            />
          ) : (
            <MatchResults
              // A new order or a new set of filters is a different list, so the
              // page and the posting open on it start again.
              key={`${sortKey}|${filters.category}|${filters.fit}|${filters.location}|${filters.company}`}
              jobs={matchedJobs}
              datasetName={datasetName}
              savedJobIds={savedJobIds}
              filtersPanel={
                isFiltersOpen ? (
                  <div className="animate-filters-in">
                    <MatchFilters
                      options={filterOptions}
                      values={filters}
                      onApply={setFilters}
                    />
                  </div>
                ) : null
              }
            />
          )}
        </Section>
      </div>

      {/* Two sections rather than two cards side by side: each chart wants
          the width of the page to be read across. */}
      <div
        className="animate-section-in"
        style={{ animationDelay: `${SECTION_STAGGER_MS * 2}ms` }}
      >
        {/* No description here: both of these carry theirs inside the card,
            level with the link out of it. */}
        <Section title="Role Fit Overview" headingSize="large">
          <RoleFitPanel
            roleScores={response.role_scores}
            datasetName={datasetName}
          />
        </Section>
      </div>

      <div
        className="animate-section-in"
        style={{ animationDelay: `${SECTION_STAGGER_MS * 3}ms` }}
      >
        <Section title="Skills worth learning next" headingSize="large">
          <SkillGapPanel
            skills={response.recommended_skills}
            byRole={response.recommended_skills_by_role}
            datasetName={datasetName}
          />
        </Section>
      </div>

      {response.resume_analysis ? (
        <div
          className="animate-section-in"
          style={{ animationDelay: `${SECTION_STAGGER_MS * 4}ms` }}
        >
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
        </div>
      ) : null}
    </div>
  );
}
