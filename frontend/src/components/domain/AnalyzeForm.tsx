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

const SEARCH_MODES: { value: SearchMode; label: string }[] = [
  { value: "tfidf", label: "Keyword" },
  { value: "semantic", label: "Semantic" },
  { value: "hybrid", label: "Hybrid" },
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
            "The analysis could not be completed.",
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
        "Could not reach the analysis service. Check that the JobLens API is running.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader
          title="Your profile"
          description="Add the skills you already have, or paste resume text for private in-memory matching."
        />
        <CardBody className="space-y-5">
          <TokenInput
            id="current-skills"
            label="Current skills"
            placeholder="Start typing a skill, then press Enter"
            hint={`${filterOptions.skills.length} skills found in this dataset. Up to 50 can be analyzed.`}
            values={currentSkills}
            suggestions={filterOptions.skills}
            onChange={setCurrentSkills}
          />

          <div>
            <p className="mb-2 text-sm font-medium text-text">Quick presets</p>
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
            label="Resume text"
            htmlFor="resume-text"
            hint="Optional. Used for this analysis only and never stored."
          >
            <textarea
              id="resume-text"
              rows={6}
              maxLength={12000}
              value={resumeText}
              onChange={(event) => setResumeText(event.target.value)}
              placeholder="Paste resume text to extract skills automatically"
              className={controlClassName}
            />
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Search scope"
          description="Narrow the job market slice this analysis is scored against."
        />
        <CardBody className="space-y-5">
          <Field
            label="Job search"
            htmlFor="search-query"
            hint="Searches titles, skills, companies, locations, and descriptions."
          >
            <input
              id="search-query"
              type="search"
              maxLength={200}
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="backend python fintech"
              className={controlClassName}
            />
          </Field>

          <fieldset>
            <legend className="mb-2 text-sm font-medium text-text">
              Search mode
            </legend>
            <div className="inline-flex rounded-lg border border-border p-0.5">
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
          </fieldset>

          <TokenInput
            id="target-roles"
            label="Target roles"
            placeholder="Start typing a job title, then press Enter"
            hint="Optional when a job search is provided. Up to 20 roles."
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
            label="Results per section"
            htmlFor="top-n"
            hint="Applies to recommended skills and matching jobs."
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
            {isSubmitting ? "Analyzing…" : "Run analysis"}
          </Button>

          {!hasProfile ? (
            <p className="text-sm text-text-muted">
              Add at least one skill or paste resume text to continue.
            </p>
          ) : null}

          {hasProfile && !hasScope ? (
            <p className="text-sm text-text-muted">
              Add a job search or at least one target role to continue.
            </p>
          ) : null}
        </div>
      </div>
    </form>
  );
}
