import { describe, expect, it } from "vitest";

import type { JobMatch } from "@/lib/api/types";
import {
  EMPTY_MATCH_FILTERS,
  filterMatches,
  matchFilterOptions,
  sortMatches,
} from "@/lib/matches";

function match(overrides: Partial<JobMatch>): JobMatch {
  return {
    job_id: "1",
    title: "Engineer",
    company: "Acme",
    company_domain: "acme.com",
    location: "Toronto, ON",
    experience_level: "Mid",
    role_category: "Software Engineering",
    date_posted: "",
    source: "",
    source_url: "",
    search_relevance: 0,
    semantic_relevance: 0,
    tfidf_relevance: 0,
    search_mode: "tfidf",
    job_match_score: 50,
    skill_match_score: 50,
    candidate_experience: "3-5 years",
    required_experience: "2+ years",
    required_experience_years: 2,
    experience_requirement_source: "description",
    experience_fit: "Close match",
    experience_fit_score: 0.5,
    matched_skills_count: 0,
    related_skills_count: 0,
    missing_skills_count: 0,
    matched_skills_preview: "None",
    related_skills_preview: "None",
    missing_skills_preview: "None",
    matched_skills: [],
    missing_skills: [],
    matched_required_skills: [],
    missing_required_skills: [],
    matched_preferred_skills: [],
    missing_preferred_skills: [],
    preferred_skill_coverage: null,
    ...overrides,
  };
}

describe("matchFilterOptions", () => {
  it("offers each value once, with the closest experience fit first", () => {
    const options = matchFilterOptions([
      match({ experience_fit: "Stretch", company: "Acme" }),
      match({ experience_fit: "Meets requirement", company: "Acme" }),
      match({ experience_fit: "Close match", company: "Beta" }),
    ]);

    expect(options.fits).toEqual([
      "Meets requirement",
      "Close match",
      "Stretch",
    ]);
    expect(options.companies).toEqual(["Acme", "Beta"]);
  });
});

describe("filterMatches", () => {
  it("keeps only the jobs that satisfy every filter at once", () => {
    const jobs = [
      match({ job_id: "1", company: "Acme", location: "Toronto, ON" }),
      match({ job_id: "2", company: "Acme", location: "Vancouver, BC" }),
      match({ job_id: "3", company: "Beta", location: "Toronto, ON" }),
    ];

    const kept = filterMatches(jobs, {
      ...EMPTY_MATCH_FILTERS,
      company: "Acme",
      location: "Toronto, ON",
    });

    expect(kept.map((job) => job.job_id)).toEqual(["1"]);
  });

  it("keeps everything when nothing is set", () => {
    const jobs = [match({ job_id: "1" }), match({ job_id: "2" })];

    expect(filterMatches(jobs, EMPTY_MATCH_FILTERS)).toHaveLength(2);
  });
});

describe("sortMatches", () => {
  const jobs = [
    match({ job_id: "1", skill_match_score: 40, date_posted: "2026-01-05" }),
    match({ job_id: "2", skill_match_score: 90, date_posted: "" }),
    match({ job_id: "3", skill_match_score: 70, date_posted: "2026-03-01" }),
  ];

  it("puts the strongest match first", () => {
    expect(sortMatches(jobs, "match_score").map((job) => job.job_id)).toEqual([
      "2",
      "3",
      "1",
    ]);
  });

  it("puts the newest first and an undated posting last", () => {
    expect(sortMatches(jobs, "date_posted").map((job) => job.job_id)).toEqual([
      "3",
      "1",
      "2",
    ]);
  });

  it("leaves the array it was handed alone", () => {
    sortMatches(jobs, "title");

    expect(jobs.map((job) => job.job_id)).toEqual(["1", "2", "3"]);
  });
});
