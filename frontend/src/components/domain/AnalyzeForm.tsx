"use client";

import { useState, type FormEvent, type ReactNode } from "react";

import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SingleSelectCombobox } from "@/components/ui/SingleSelectCombobox";
import {
  largeControlClassName,
  noticeToneClassName,
  outlineControlButtonClassName,
  type Notice,
} from "@/components/ui/Field";
import { ErrorState } from "@/components/ui/States";
import { TokenInput } from "@/components/ui/TokenInput";
import { useAnalysis } from "@/context/AnalysisContext";
import { formatSkill } from "@/lib/format";
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  FilterOptions,
} from "@/lib/api/types";

/** Matches returned for the results view to filter by category. */
const RESULT_LIMIT = 45;

const EXPERIENCE_BUCKETS = [
  "0-1 years",
  "1-2 years",
  "2-3 years",
  "3-4 years",
  "4-5 years",
  "5-7 years",
  "7-10 years",
  "10+ years",
];

function ProfileIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c0-3.6 3.1-5.5 7-5.5s7 1.9 7 5.5" />
    </svg>
  );
}

function CompassIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="8.5" />
      <path d="m15.5 8.5-2 5-5 2 2-5z" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect x="4.5" y="10.5" width="15" height="9.5" rx="2" />
      <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

/** An area of the form, announced by its own icon and label. */
function SectionHeading({
  icon,
  children,
}: {
  icon: ReactNode;
  children: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="inline-flex shrink-0 rounded-xl bg-accent-soft p-2 text-accent">
        {icon}
      </span>
      <h2 className="text-base font-semibold uppercase tracking-wide text-text">
        {children}
      </h2>
    </div>
  );
}

/** The hint under a control, kept to one voice across the form. */
function FieldHint({ children }: { children: string }) {
  return <p className="mt-2 text-xs text-text-subtle">{children}</p>;
}

export function AnalyzeForm({
  filterOptions,
  datasetName,
}: {
  filterOptions: FilterOptions;
  datasetName: string;
}) {
  const { setAnalysis } = useAnalysis();

  const [currentSkills, setCurrentSkills] = useState<string[]>([]);
  const [resumeText, setResumeText] = useState("");
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractNotice, setExtractNotice] = useState<Notice | null>(null);
  const [candidateExperience, setCandidateExperience] = useState("");

  const [location, setLocation] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [validationMessage, setValidationMessage] = useState("");

  /**
   * Pulls skills out of the pasted resume and turns them into tags, leaving
   * the person on the same step so they can keep adding to them.
   */
  async function handleExtractSkills() {
    const text = resumeText.trim();

    if (!text) {
      setExtractNotice({
        text: "Paste your resume first, then read the skills from it.",
        tone: "error",
      });
      return;
    }

    setIsExtracting(true);
    setExtractNotice(null);

    try {
      const response = await fetch("/proxy/resume-skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Scoped to the active dataset so the resume box recognises the
        // same skills the list on this form offers.
        body: JSON.stringify({ resume_text: text, dataset_name: datasetName }),
      });

      const payload = await response.json();

      if (!response.ok) {
        setExtractNotice({
          text:
            (payload as { detail?: string }).detail ??
            "We could not read skills from that resume.",
          tone: "error",
        });
        return;
      }

      const found = (payload as { skills: string[] }).skills;

      if (found.length === 0) {
        setExtractNotice({
          text: "No skills we recognise turned up in that text. Add them from the list instead.",
          tone: "error",
        });
        return;
      }

      // Merging rather than replacing: anything already chosen by hand stays.
      const seenKeys = new Set(
        currentSkills.map((skill) => skill.toLowerCase()),
      );
      const additions = found.filter((skill) => {
        const key = skill.toLowerCase();

        if (seenKeys.has(key)) {
          return false;
        }

        seenKeys.add(key);
        return true;
      });

      if (additions.length > 0) {
        setCurrentSkills([...currentSkills, ...additions].slice(0, 50));
        setValidationMessage("");
      }

      // Read, so the box is done with: leaving the text sitting there reads
      // as though it still has to be submitted.
      setResumeText("");

      setExtractNotice(
        additions.length === 0
          ? {
              text: "Every skill in that resume was already on your list.",
              tone: "error",
            }
          : {
              text: `Added ${additions.length} ${additions.length === 1 ? "skill" : "skills"} from your resume.`,
              tone: "success",
            },
      );
    } catch {
      setExtractNotice({
        text: "Could not reach JobLens. Check your connection.",
        tone: "error",
      });
    } finally {
      setIsExtracting(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (currentSkills.length === 0 && !resumeText.trim()) {
      setValidationMessage(
        "Choose at least one skill, or paste your resume below.",
      );
      return;
    }

    if (!candidateExperience) {
      setValidationMessage("Choose how much experience you have.");
      return;
    }

    if (!location) {
      setValidationMessage("Choose a location, or pick Any location.");
      return;
    }

    setValidationMessage("");
    setErrorMessage("");
    setIsSubmitting(true);

    const request: AnalyzeRequest = {
      current_skills: currentSkills,
      resume_text: resumeText,
      target_roles: [],
      // No role or query narrows the search any more: skills and location
      // define it, and the results view filters by category afterwards.
      search_query: "",
      search_mode: "tfidf",
      location,
      experience_level: "Any",
      // Enough matches that a single category still has depth to show.
      top_jobs: RESULT_LIMIT,
      candidate_experience: candidateExperience,
      dataset_name: datasetName,
    };

    try {
      const response = await fetch("/proxy/analyze", {
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
    } catch {
      setErrorMessage(
        "Could not reach JobLens. Check your connection and try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const notices = (
    <>
      {validationMessage ? (
        <p role="alert" className={`mt-4 ${noticeToneClassName.error}`}>
          {validationMessage}
        </p>
      ) : null}

      {errorMessage ? (
        <div className="mt-4">
          <ErrorState
            title="Analysis could not run"
            description={errorMessage}
          />
        </div>
      ) : null}
    </>
  );

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <Card className="relative overflow-visible">
        <CardBody className="overflow-visible p-5 pb-24 sm:px-6 sm:pt-7 sm:pb-24">
          <SectionHeading icon={<ProfileIcon />}>Your profile</SectionHeading>

          <div className="mt-5">
            <TokenInput
              id="current-skills"
              label="Skills"
              placeholder="Choose skill(s)"
              values={currentSkills}
              suggestions={filterOptions.skills}
              allowCustomValues={false}
              required
              formatValue={formatSkill}
              onChange={(skills) => {
                setValidationMessage("");
                setCurrentSkills(skills);
              }}
            />
            <FieldHint>
              Choose the skills you currently feel comfortable using
            </FieldHint>
          </div>

          {/* The two routes to the same field, so neither reads as the
              fallback for the other. */}
          <div className="my-6 flex items-center gap-4">
            <span className="h-px flex-1 bg-border" />
            <span className="text-sm text-text-muted">
              or add skills from your resume
            </span>
            <span className="h-px flex-1 bg-border" />
          </div>

          <div>
            <textarea
              id="resume-text"
              aria-label="Paste your resume"
              rows={3}
              maxLength={12000}
              value={resumeText}
              onChange={(event) => {
                setResumeText(event.target.value);
                setExtractNotice(null);
              }}
              placeholder="Paste your resume"
              className={`${largeControlClassName} min-h-[84px] resize-y`}
            />

            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleExtractSkills}
                disabled={isExtracting}
                className={outlineControlButtonClassName}
              >
                {isExtracting ? "Reading…" : "Read skills from resume"}
              </button>

              {extractNotice ? (
                <p
                  role="status"
                  className={noticeToneClassName[extractNotice.tone]}
                >
                  {extractNotice.text}
                </p>
              ) : null}
            </div>

            <p className="mt-3 flex items-center gap-1.5 text-xs text-text-subtle">
              <LockIcon />
              Your resume is only used to work out this result. It is never
              saved or shared
            </p>
          </div>

          <div className="mt-8 border-t border-border pt-7">
            <SectionHeading icon={<CompassIcon />}>
              Experience &amp; location
            </SectionHeading>

            <div className="mt-5 grid gap-6 sm:grid-cols-2">
              <div>
                <SingleSelectCombobox
                  id="candidate-experience"
                  label="Experience Level"
                  value={candidateExperience}
                  placeholder="Select experience"
                  required
                  options={EXPERIENCE_BUCKETS.map((option) => ({
                    value: option,
                    label: option,
                  }))}
                  onChange={(next) => {
                    setValidationMessage("");
                    setCandidateExperience(next);
                  }}
                />
                <FieldHint>
                  How much professional experience do you have?
                </FieldHint>
              </div>

              <div>
                <SingleSelectCombobox
                  id="location"
                  label="Location"
                  value={location}
                  placeholder="Select location"
                  required
                  options={[
                    { value: "Any", label: "Any location" },
                    ...filterOptions.locations.map((option) => ({
                      value: option,
                      label: option,
                    })),
                  ]}
                  onChange={(next) => {
                    setValidationMessage("");
                    setLocation(next);
                  }}
                />
                <FieldHint>Jobs near this location will be prioritized</FieldHint>
              </div>
            </div>
          </div>

          {notices}
        </CardBody>

        {/* Sticky visual bottom of the card */}
        <div className="sticky bottom-0 z-20 -mx-px bg-canvas">
          <div className="flex justify-center rounded-b-xl border border-border bg-surface px-5 py-4 sm:px-6">
            <Button
              type="submit"
              size="md"
              variant="strong"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Checking…" : "Analyze my fit"}
              <span aria-hidden="true" className="ml-2">
                &rarr;
              </span>
            </Button>
          </div>
        </div>
      </Card>
    </form>
  );
}
