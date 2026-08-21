"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  deleteAnalysisRunAction,
  renameAnalysisRunAction,
  type HistoryActionResult,
} from "@/app/history/actions";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { controlClassName } from "@/components/ui/Field";
import { useAnalysis } from "@/context/AnalysisContext";
import { useToast } from "@/context/ToastContext";
import type { AnalysisRun, AnalyzeRequest, AnalyzeResponse } from "@/lib/api/types";
import { withDataset } from "@/lib/datasets";
import { formatCount, formatDate, formatPercent, formatSkill } from "@/lib/format";

export function AnalysisRunRow({ run }: { run: AnalysisRun }) {
  const router = useRouter();
  const { showToast } = useToast();
  const { setAnalysis } = useAnalysis();
  const [isRenaming, setIsRenaming] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [newName, setNewName] = useState(run.name);
  const [isBusy, setIsBusy] = useState(false);
  const [isOpening, setIsOpening] = useState(false);

  /*
   * A saved run keeps what was asked and the headline of what came back, not
   * the matched postings or the per-role rankings the result view draws. So
   * opening one runs the analysis again from the inputs it kept. The dataset
   * may have moved on since, which is the honest answer rather than a
   * reconstruction from a summary.
   */
  async function openRun() {
    setIsOpening(true);

    const request: AnalyzeRequest = {
      current_skills: run.current_skills,
      resume_text: "",
      target_roles: run.target_roles,
      search_query: "",
      search_mode: "tfidf",
      location: run.location,
      experience_level: run.experience_level,
      candidate_experience: "Not specified",
      dataset_name: run.dataset_name,
    };

    try {
      const httpResponse = await fetch("/proxy/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      if (!httpResponse.ok) {
        const body = (await httpResponse.json().catch(() => null)) as {
          detail?: string;
        } | null;

        showToast(body?.detail ?? "That result could not be opened.", "error");
        return;
      }

      const response = (await httpResponse.json()) as AnalyzeResponse;

      setAnalysis(
        {
          request,
          response,
          completedAt: new Date().toISOString(),
        },
        // It came out of history, so offering to save it again would only
        // write the same run a second time.
        { alreadySaved: true },
      );

      router.push(withDataset("/analyze", run.dataset_name));
    } catch {
      showToast("Could not reach JobLens. Check your connection.", "error");
    } finally {
      setIsOpening(false);
    }
  }

  async function runAction(action: () => Promise<HistoryActionResult>) {
    setIsBusy(true);

    const result = await action();

    if (result.ok) {
      setIsRenaming(false);
      setIsConfirmingDelete(false);
      showToast(result.message);
    } else {
      showToast(result.message, "error");
    }

    setIsBusy(false);
  }

  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <button
            type="button"
            onClick={openRun}
            disabled={isOpening}
            className="block max-w-full truncate text-left text-sm font-medium text-text hover:underline disabled:opacity-60"
          >
            {isOpening ? `Opening ${run.name}…` : run.name}
          </button>
          <p className="mt-0.5 text-xs text-text-muted">
            {run.dataset_name} · {formatDate(run.created_at)} ·{" "}
            {formatCount(run.jobs_analyzed)} jobs
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {run.best_role ? <Badge tone="neutral">{run.best_role}</Badge> : null}
          {run.top_missing_skill ? (
            <Badge tone="warning">
              Gap: {formatSkill(run.top_missing_skill)}
            </Badge>
          ) : null}
          <span className="text-sm font-semibold tabular-nums text-text">
            {run.weighted_match_score === null
              ? "N/A"
              : formatPercent(run.weighted_match_score)}
          </span>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsRenaming((open) => !open)}
            aria-expanded={isRenaming}
          >
            Rename
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={isBusy}
            onClick={() => setIsConfirmingDelete(true)}
          >
            Delete
          </Button>
        </div>
      </div>

      {isRenaming ? (
        <form
          className="mt-3 flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            runAction(() => renameAnalysisRunAction(run.id, newName));
          }}
        >
          <div className="min-w-0 flex-1">
            <label
              htmlFor={`rename-run-${run.id}`}
              className="block text-sm font-medium text-text"
            >
              New name
            </label>
            <input
              id={`rename-run-${run.id}`}
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              required
              maxLength={255}
              className={`mt-1.5 ${controlClassName}`}
            />
          </div>
          <Button type="submit" size="sm" disabled={isBusy}>
            {isBusy ? "Saving…" : "Save name"}
          </Button>
        </form>
      ) : null}

      <ConfirmDialog
        open={isConfirmingDelete}
        title={`Delete ${run.name}?`}
        description="This permanently removes this saved result. The jobs and skills it was based on are not affected, and you can always run the check again."
        confirmLabel="Delete result"
        isBusy={isBusy}
        onCancel={() => setIsConfirmingDelete(false)}
        onConfirm={() => runAction(() => deleteAnalysisRunAction(run.id, run.name))}
      />
    </li>
  );
}
