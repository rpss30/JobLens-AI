"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Field, controlClassName } from "@/components/ui/Field";
import { ErrorState } from "@/components/ui/States";
import { TokenInput } from "@/components/ui/TokenInput";
import { useAnalysis } from "@/context/AnalysisContext";
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  FilterOptions,
  SearchMode,
} from "@/lib/api/types";

const PROFILE_PRESETS: Record<string, string[]> = {
  "Backend developer": ["Python", "REST APIs", "PostgreSQL", "Docker", "AWS"],
  "Data scientist": ["Python", "SQL", "Pandas", "scikit-learn", "statistics"],
  "ML engineer": ["Python", "PyTorch", "TensorFlow", "Docker", "AWS"],
  "Cloud engineer": ["AWS", "Docker", "Terraform", "Kubernetes", "CI/CD"],
};

const SEARCH_MODES: { value: SearchMode; label: string; hint: string }[] = [
  {
    value: "tfidf",
    label: "Exact words",
    hint: "Finds jobs containing the words you typed.",
  },
  {
    value: "semantic",
    label: "Similar meaning",
    hint: "Also finds jobs that mean the same thing in different words.",
  },
  {
    value: "hybrid",
    label: "Both",
    hint: "Blends exact wording with similar meaning.",
  },
];

const EXPERIENCE_BUCKETS = [
  "Not specified",
  "0-1 years",
  "1-2 years",
  "3-5 years",
  "5-8 years",
  "8+ years",
];

export function AnalyzeForm({
  filterOptions,
  datasetName,
}: {
  filterOptions: FilterOptions;
  datasetName: string;
}) {
  const router = useRouter();
  const { setAnalysis } = useAnalysis();

  const [currentSkills, setCurrentSkills] = useState<string[]>([]);
  const [targetRoles, setTargetRoles] = useState<string[]>([]);
  const [resumeText, setResumeText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMode, setSearchMode] = useState<SearchMode>("tfidf");
  const [location, setLocation] = useState("Any");
  const [experienceLevel, setExperienceLevel] = useState("Any");
  const [candidateExperience, setCandidateExperience] = useState("Not specified");
  const [topN, setTopN] = useState(10);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const hasProfile = currentSkills.length > 0 || resumeText.trim().length > 0;
  const hasScope =
    searchQuery.trim().length > 0 ||
    targetRoles.length > 0 ||
    resumeText.trim().length > 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage("");
    setIsSubmitting(true);

    const request: AnalyzeRequest = {
      current_skills: currentSkills,
      resume_text: resumeText,
      target_roles: targetRoles,
      search_query: searchQuery,
      search_mode: searchMode,
      location,
      experience_level: experienceLevel,
      candidate_experience: candidateExperience,
      top_n: topN,
      dataset_name: datasetName,
    };

    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      const payload = await response.json();

      if (!response.ok) {
        setErrorMessage(
          (payload as { detail?: string }).detail ??
            "We could not check your skills just now.",
        );
        return;
      }

      setAnalysis({
        request,
        response: payload as AnalyzeResponse,
        completedAt: new Date().toISOString(),
      });
      router.push(`/?dataset=${encodeURIComponent(datasetName)}`);
    } catch {
      setErrorMessage(
        "Could not reach JobLens. Check your connection and try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader
          title="What you can do"
          description="List the skills you already have, or paste your resume and we will pull them out."
        />
        <CardBody className="space-y-5">
          <TokenInput
            id="current-skills"
            label="Skills you have"
            placeholder="Type a skill, for example Python"
            hint={`Pick from ${filterOptions.skills.length} skills these employers ask for, or type your own. Up to 50.`}
            values={currentSkills}
            suggestions={filterOptions.skills}
            onChange={setCurrentSkills}
          />

          <div>
            <p className="mb-2 text-sm font-medium text-text">Or start from a common profile</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(PROFILE_PRESETS).map(([name, skills]) => (
                <Button
                  key={name}
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setCurrentSkills(skills)}
                >
                  {name}
                </Button>
              ))}
            </div>
          </div>

          <Field
            label="Or paste your resume"
            htmlFor="resume-text"
            hint="Optional. Used only to work out this result, and never saved or shared."
          >
            <textarea
              id="resume-text"
              rows={6}
              maxLength={12000}
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
              placeholder="Paste your resume here and we will find your skills for you"
              className={controlClassName}
            />
          </Field>

          <Field
            label="Relevant professional experience"
            htmlFor="candidate-experience"
            hint="Optional. Shown separately from skill fit."
          >
            <select
              id="candidate-experience"
              value={candidateExperience}
              onChange={(event) => setCandidateExperience(event.target.value)}
              className={controlClassName}
            >
              {EXPERIENCE_BUCKETS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Which jobs to compare against"
          description="Leave these as they are to use every job, or narrow it down to what you are looking for."
        />
        <CardBody className="space-y-5">
          <Field
            label="What kind of job?"
            htmlFor="search-query"
            hint="Looks through job titles, skills, companies, locations, and full descriptions."
          >
            <input
              id="search-query"
              type="search"
              maxLength={200}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="for example, backend developer"
              className={controlClassName}
            />
          </Field>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-text">
              How to match your search
            </legend>
            <div className="inline-flex flex-wrap rounded-lg border border-border p-0.5">
              {SEARCH_MODES.map((mode) => (
                <button
                  key={mode.value}
                  type="button"
                  aria-pressed={searchMode === mode.value}
                  onClick={() => setSearchMode(mode.value)}
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    searchMode === mode.value
                      ? "bg-accent-soft text-accent"
                      : "text-text-muted hover:text-text"
                  }`}
                >
                  {mode.label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-text-subtle">
              {SEARCH_MODES.find((mode) => mode.value === searchMode)?.hint}
            </p>
          </fieldset>

          <TokenInput
            id="target-roles"
            label="Job titles you are aiming for"
            placeholder="Type a job title, for example Data Analyst"
            hint="Optional. Add job titles you are aiming for, up to 20."
            values={targetRoles}
            suggestions={filterOptions.target_roles}
            maxValues={20}
            onChange={setTargetRoles}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Location" htmlFor="location">
              <select
                id="location"
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                className={controlClassName}
              >
                <option value="Any">Any location</option>
                {filterOptions.locations.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Experience level" htmlFor="experience-level">
              <select
                id="experience-level"
                value={experienceLevel}
                onChange={(event) => setExperienceLevel(event.target.value)}
                className={controlClassName}
              >
                <option value="Any">Any level</option>
                {filterOptions.experience_levels.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <Field
            label="How many results to show"
            htmlFor="top-n"
            hint="Applies to the skills list and the job matches."
          >
            <input
              id="top-n"
              type="number"
              min={1}
              max={25}
              value={topN}
              onChange={(event) => setTopN(Number(event.target.value))}
              className={controlClassName}
            />
          </Field>
        </CardBody>
      </Card>

      <div className="lg:col-span-2">
        {errorMessage ? (
          <ErrorState
            title="Analysis could not run"
            description={errorMessage}
            className="mb-4"
          />
        ) : null}

        <div className="flex flex-wrap items-center gap-4">
          <Button type="submit" disabled={isSubmitting || !hasProfile || !hasScope}>
            {isSubmitting ? "Checking your skills…" : "Check my skills"}
          </Button>

          {!hasProfile ? (
            <p className="text-sm text-text-muted">
              Add at least one skill, or paste your resume, to continue.
            </p>
          ) : null}

          {hasProfile && !hasScope ? (
            <p className="text-sm text-text-muted">
              Type what kind of job you are looking for, or add a target role, to continue.
            </p>
          ) : null}
        </div>
      </div>
    </form>
  );
}
