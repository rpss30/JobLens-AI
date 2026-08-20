import type { JobMatch } from "@/lib/api/types";

/**
 * Narrowing and ordering the matched jobs.
 *
 * None of it goes through the API. A result lives in memory on the client, so
 * re-running the analysis to reorder six cards would be a round trip for work
 * the page can already do.
 */

/** The value every filter starts at, and the one that narrows nothing. */
export const ANY_FILTER_VALUE = "Any";

export interface MatchFilterValues {
  category: string;
  fit: string;
  location: string;
  company: string;
}

export const EMPTY_MATCH_FILTERS: MatchFilterValues = {
  category: ANY_FILTER_VALUE,
  fit: ANY_FILTER_VALUE,
  location: ANY_FILTER_VALUE,
  company: ANY_FILTER_VALUE,
};

/**
 * What the matching engine calls each fit, and what a card calls it.
 *
 * "Meets requirement" is the engine's own wording and is too long to sit
 * beside the years it describes.
 */
const EXPERIENCE_FIT_LABELS: Record<string, string> = {
  "Meets requirement": "Matched",
  "Close match": "Close Match",
  Stretch: "Stretch",
};

/** Best fit first, rather than the alphabetical order the data arrives in. */
const EXPERIENCE_FIT_ORDER = ["Meets requirement", "Close match", "Stretch"];

export function experienceFitLabel(fit: string): string {
  return EXPERIENCE_FIT_LABELS[fit] ?? fit;
}

/*
 * No relevance option. The API ranks a match on search relevance first and
 * its score second, and an analysis carries no search query, so relevance
 * and match score produced the same order under two names.
 */
export type MatchSortKey =
  | "match_score"
  | "date_posted"
  | "title"
  | "company"
  | "location";

export const MATCH_SORT_LABELS: Record<MatchSortKey, string> = {
  match_score: "Match score",
  date_posted: "Date posted",
  title: "Title",
  company: "Company",
  location: "Location",
};

function uniqueSorted(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))].sort((first, second) =>
    first.localeCompare(second),
  );
}

export interface MatchFilterOptions {
  categories: string[];
  fits: string[];
  locations: string[];
  companies: string[];
}

/**
 * The values worth offering, taken from the matches themselves.
 *
 * A fixed list off the dataset would offer companies and places that none of
 * these postings are in, so every choice here leads somewhere.
 */
export function matchFilterOptions(jobs: JobMatch[]): MatchFilterOptions {
  return {
    categories: uniqueSorted(jobs.map((job) => job.role_category)),
    fits: uniqueSorted(jobs.map((job) => job.experience_fit)).sort(
      (first, second) =>
        EXPERIENCE_FIT_ORDER.indexOf(first) -
        EXPERIENCE_FIT_ORDER.indexOf(second),
    ),
    locations: uniqueSorted(jobs.map((job) => job.location)),
    companies: uniqueSorted(jobs.map((job) => job.company)),
  };
}

/**
 * What the filters start at for a fresh result.
 *
 * Narrowed to the role the analysis settled on: that role is the finding, and
 * the postings worth reading first are the ones under it. A best role that no
 * match carries would narrow the list to nothing, so that falls back to all
 * of them.
 */
export function defaultMatchFilters(
  jobs: JobMatch[],
  bestRole: string,
): MatchFilterValues {
  const isWorthNarrowing =
    Boolean(bestRole) && jobs.some((job) => job.role_category === bestRole);

  return isWorthNarrowing
    ? { ...EMPTY_MATCH_FILTERS, category: bestRole }
    : EMPTY_MATCH_FILTERS;
}

export function filterMatches(
  jobs: JobMatch[],
  values: MatchFilterValues,
): JobMatch[] {
  return jobs.filter(
    (job) =>
      (values.category === ANY_FILTER_VALUE ||
        job.role_category === values.category) &&
      (values.fit === ANY_FILTER_VALUE ||
        job.experience_fit === values.fit) &&
      (values.location === ANY_FILTER_VALUE ||
        job.location === values.location) &&
      (values.company === ANY_FILTER_VALUE ||
        job.company === values.company),
  );
}

export function activeMatchFilterCount(values: MatchFilterValues): number {
  return Object.values(values).filter((value) => value !== ANY_FILTER_VALUE)
    .length;
}

export function sortMatches(jobs: JobMatch[], key: MatchSortKey): JobMatch[] {
  const sorted = [...jobs];

  if (key === "match_score") {
    return sorted.sort(
      (first, second) => second.skill_match_score - first.skill_match_score,
    );
  }

  if (key === "date_posted") {
    // Newest first, and a posting that never recorded a date goes last rather
    // than to the top of the list on an empty string.
    return sorted.sort((first, second) =>
      second.date_posted.localeCompare(first.date_posted),
    );
  }

  return sorted.sort((first, second) => first[key].localeCompare(second[key]));
}
