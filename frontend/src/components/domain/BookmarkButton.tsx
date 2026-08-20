"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useToast } from "@/context/ToastContext";
import type { JobDetail } from "@/lib/api/types";

/**
 * Keeps a posting, or lets it go.
 *
 * The saved state is held here rather than re-read from the server on every
 * click, so the mark responds at once; a failure puts it back and says why.
 */
export function BookmarkButton({
  job,
  datasetName,
  initiallySaved,
}: {
  job: JobDetail;
  datasetName: string;
  initiallySaved: boolean;
}) {
  const router = useRouter();
  const { showToast } = useToast();
  const [isSaved, setIsSaved] = useState(initiallySaved);
  const [isBusy, setIsBusy] = useState(false);

  async function toggleSaved() {
    const wasSaved = isSaved;

    setIsBusy(true);
    setIsSaved(!wasSaved);

    try {
      const response = wasSaved
        ? await fetch(
            `/proxy/saved-jobs/${encodeURIComponent(job.job_id)}?dataset_name=${encodeURIComponent(datasetName)}`,
            { method: "DELETE" },
          )
        : await fetch("/proxy/saved-jobs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              job_id: job.job_id,
              dataset_name: datasetName,
              title: job.title,
              company: job.company,
              location: job.location,
              source_url: job.source_url,
            }),
          });

      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as {
          detail?: string;
        } | null;

        throw new Error(body?.detail ?? "That did not work.");
      }

      showToast(wasSaved ? "Removed from saved jobs." : "Saved this job.");
      router.refresh();
    } catch (error) {
      setIsSaved(wasSaved);
      showToast(
        error instanceof Error ? error.message : "Could not save this job.",
      );
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={toggleSaved}
      disabled={isBusy}
      aria-pressed={isSaved}
      aria-label={isSaved ? "Remove from saved jobs" : "Save this job"}
      title={isSaved ? "Remove from saved jobs" : "Save this job"}
      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border transition-colors disabled:opacity-60 ${
        isSaved
          ? "border-accent bg-accent-soft text-accent"
          : "border-border text-text-muted hover:bg-surface-muted"
      }`}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 20 20"
        fill={isSaved ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M5.25 3.75h9.5v13l-4.75-3.25-4.75 3.25v-13Z" />
      </svg>
    </button>
  );
}
