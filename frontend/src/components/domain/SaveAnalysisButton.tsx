"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";

/** A floppy disk: the same mark the rest of the web uses for keeping a thing. */
function SaveIcon() {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M4.75 3.75h8L16.25 7v9.25a1 1 0 0 1-1 1H4.75a1 1 0 0 1-1-1V4.75a1 1 0 0 1 1-1Z" />
      <path d="M6.75 3.75v4h5v-4M6.75 17v-4.5h6.5V17" />
    </svg>
  );
}
import { useAnalysis } from "@/context/AnalysisContext";
import { useToast } from "@/context/ToastContext";
import type { CreateAnalysisRunRequest } from "@/lib/api/types";

type SaveState = "idle" | "saving";

export function SaveAnalysisButton() {
  const router = useRouter();
  const { analysis, isAnalysisSaved, markAnalysisSaved } = useAnalysis();
  const { showToast } = useToast();
  const [saveState, setSaveState] = useState<SaveState>("idle");

  if (!analysis) {
    return null;
  }

  async function handleSave() {
    if (!analysis) {
      return;
    }

    setSaveState("saving");

    const { request, response } = analysis;

    const payload: CreateAnalysisRunRequest = {
      name: "",
      dataset_name: response.dataset_name,
      target_roles: request.target_roles,
      location: request.location,
      experience_level: request.experience_level,
      current_skills:
        response.resume_analysis?.combined_skills.slice(0, 50) ??
        request.current_skills,
      best_role: response.best_role,
      weighted_match_score: response.weighted_match_score,
      top_missing_skill: response.top_missing_skill,
      jobs_analyzed: response.jobs_analyzed,
      recommended_skills: response.recommended_skills.map((item) => item.skill),
      // The API caps saved role scores, so send the ranked head only.
      role_scores: response.role_scores.slice(0, 20) as unknown as Record<
        string,
        unknown
      >[],
    };

    try {
      const httpResponse = await fetch("/proxy/analysis-runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!httpResponse.ok) {
        const body = (await httpResponse.json()) as { detail?: string };
        showToast(
          body.detail ?? "This result could not be saved.",
          "error",
        );
        return;
      }

      markAnalysisSaved();
      showToast("Saved to your history.");
      router.refresh();
    } catch {
      showToast("Could not reach JobLens. Check your connection.", "error");
    } finally {
      setSaveState("idle");
    }
  }

  const label =
    saveState === "saving"
      ? "Saving…"
      : isAnalysisSaved
        ? "Saved to History"
        : "Save to History";

  return (
    <Button
      variant="secondary"
      size="iconOnlyMobile"
      onClick={handleSave}
      disabled={saveState === "saving" || isAnalysisSaved}
      disabledCursor={isAnalysisSaved ? "default" : "not-allowed"}
      // The label is the only thing that goes on a phone; the mark stays, so
      // the button is still named to anything not looking at it.
      aria-label={label}
      title={label}
    >
      <span className="hidden sm:inline">{label}</span>
      <SaveIcon />
    </Button>
  );
}
