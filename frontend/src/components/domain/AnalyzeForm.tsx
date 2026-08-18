"use client";

import { useRouter } from "next/navigation";
import {
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";

import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  RequiredMark,
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

function StepHeading({ children }: { children: string }) {
  return (
    <h2 className="text-2xl font-semibold uppercase tracking-wide text-text">
      {children}
    </h2>
  );
}

function SingleSelectCombobox({
  id,
  label,
  value,
  placeholder,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  placeholder: string;
  options: {
    value: string;
    label: string;
  }[];
  onChange: (value: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [menuPlacement, setMenuPlacement] = useState<"up" | "down">("down");
  const [menuMaxHeight, setMenuMaxHeight] = useState(288);

  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const listId = useId();

  function openMenu() {
    const currentIndex = options.findIndex((option) => option.value === value);

    setActiveIndex(currentIndex >= 0 ? currentIndex : 0);
    setIsOpen(true);
  }

  function closeMenu() {
    setIsOpen(false);
    setActiveIndex(-1);
  }

  function selectOption(option: { value: string; label: string }) {
    onChange(option.value);
    closeMenu();

    requestAnimationFrame(() => {
      buttonRef.current?.focus();
    });
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();

      if (!isOpen) {
        openMenu();
        return;
      }

      setActiveIndex((index) => (index >= options.length - 1 ? 0 : index + 1));
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();

      if (!isOpen) {
        openMenu();
        return;
      }

      setActiveIndex((index) => (index <= 0 ? options.length - 1 : index - 1));
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();

      if (!isOpen) {
        openMenu();
        return;
      }

      if (activeIndex >= 0 && options[activeIndex]) {
        selectOption(options[activeIndex]);
      }

      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu();
    }
  }

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function updateMenuPlacement() {
      const button = buttonRef.current;

      if (!button) {
        return;
      }

      const rect = button.getBoundingClientRect();

      const viewportTop = window.visualViewport?.offsetTop ?? 0;
      const viewportHeight =
        window.visualViewport?.height ?? window.innerHeight;
      const viewportBottom = viewportTop + viewportHeight;

      const gap = 8;
      const preferredHeight = 288;
      const minimumUsefulHeight = 160;

      const spaceBelow = Math.max(0, viewportBottom - rect.bottom - gap);

      const spaceAbove = Math.max(0, rect.top - viewportTop - gap);

      const shouldOpenUp =
        spaceBelow < minimumUsefulHeight && spaceAbove > spaceBelow;

      const availableSpace = shouldOpenUp ? spaceAbove : spaceBelow;

      setMenuPlacement(shouldOpenUp ? "up" : "down");
      setMenuMaxHeight(Math.max(96, Math.min(preferredHeight, availableSpace)));
    }

    updateMenuPlacement();

    window.addEventListener("resize", updateMenuPlacement);
    window.addEventListener("scroll", updateMenuPlacement, true);

    return () => {
      window.removeEventListener("resize", updateMenuPlacement);
      window.removeEventListener("scroll", updateMenuPlacement, true);
    };
  }, [isOpen]);

  return (
    <div className="space-y-3">
      <label htmlFor={id} className="block text-base font-medium text-text">
        {label}
      </label>

      <div
        className="relative"
        onBlur={(event) => {
          if (
            !event.currentTarget.contains(event.relatedTarget as Node | null)
          ) {
            closeMenu();
          }
        }}
      >
        <RequiredMark />

        <button
          ref={buttonRef}
          id={id}
          type="button"
          role="combobox"
          aria-expanded={isOpen}
          aria-controls={listId}
          aria-haspopup="listbox"
          className={`${largeControlClassName} flex w-full items-center justify-between pr-10 text-left ${
            value ? "text-text" : "text-text-subtle"
          }`}
          onClick={() => {
            if (isOpen) {
              closeMenu();
            } else {
              openMenu();
            }
          }}
          onKeyDown={handleKeyDown}
        >
          <span>
            {options.find((option) => option.value === value)?.label ||
              placeholder}
          </span>
        </button>

        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
          className={`pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-subtle transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        >
          <path
            d="M4.5 6.25 8 9.75l3.5-3.5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {isOpen ? (
          <ul
            id={listId}
            role="listbox"
            aria-label={`${label} options`}
            style={{ maxHeight: menuMaxHeight }}
            className={`absolute left-0 right-0 z-50 overflow-y-auto overscroll-contain rounded-lg border border-border bg-surface py-1 shadow-lg ${
              menuPlacement === "up" ? "bottom-full mb-1" : "top-full mt-1"
            }`}
          >
            {options.map((option, index) => (
              <li key={option.value}>
                <button
                  type="button"
                  role="option"
                  aria-selected={option.value === value}
                  className={`block w-full px-3 py-2 text-left text-sm ${
                    index === activeIndex
                      ? "bg-accent-soft text-accent"
                      : "text-text hover:bg-surface-muted"
                  }`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => selectOption(option)}
                >
                  {option.label}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

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
    <form onSubmit={handleSubmit} className="w-full">
      <Card className="overflow-visible">
        <CardBody className="overflow-visible p-5 sm:px-5 sm:py-7">
          <div className="flex flex-col">
            {/* Heading */}
            <StepHeading>What do you bring?</StepHeading>

            {/* Skills */}
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
            </div>

            {/* Resume alternative */}
            <div className="mt-3">
              <p className="mb-2 pl-2 text-sm text-text-subtle">OR</p>

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

              <p className="mt-2 text-xs text-text-subtle">
                Your resume is only used to work out this result. It is never
                saved or shared.
              </p>
            </div>

            {/* Experience */}
            <div className="mt-7">
              <SingleSelectCombobox
                id="candidate-experience"
                label="Experience Level"
                value={candidateExperience}
                placeholder="Select experience"
                options={EXPERIENCE_BUCKETS.map((option) => ({
                  value: option,
                  label: option,
                }))}
                onChange={(next) => {
                  setValidationMessage("");
                  setCandidateExperience(next);
                }}
              />
            </div>

            {validationMessage ? (
              <p role="alert" className={`mt-3 ${noticeToneClassName.error}`}>
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

            {/* Location */}
            <div className="mt-7">
              <SingleSelectCombobox
                id="location"
                label="Location"
                value={location}
                placeholder="Select location"
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
            </div>

            {validationMessage ? (
              <p role="alert" className={`mt-3 ${noticeToneClassName.error}`}>
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

            <div className="mt-auto flex justify-end pt-10">
              <Button type="submit" size="lg" disabled={isSubmitting}>
                {isSubmitting ? "Checking…" : "Submit"}
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>
    </form>
  );
}
