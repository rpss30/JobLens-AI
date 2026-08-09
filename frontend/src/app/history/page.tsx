import Link from "next/link";

import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { ApiError } from "@/lib/api/client";
import { getAnalysisRuns } from "@/lib/api/endpoints";
import type { AnalysisRun } from "@/lib/api/types";
import { resolveDataset } from "@/lib/datasets";
import { formatCount, formatDate, formatPercent, formatSkill } from "@/lib/format";

function AnalysisRunRow({ run }: { run: AnalysisRun }) {
  return (
    <li>
      <Link
        href={`/history/${run.id}`}
        className="flex flex-wrap items-center justify-between gap-4 px-5 py-4 hover:bg-surface-muted"
      >
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-text">{run.name}</p>
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
        </div>
      </Link>
    </li>
  );
}

export default async function HistoryPage({
  searchParams,
}: PageProps<"/history">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  let runs: AnalysisRun[] = [];
  let loadError: string | null = null;

  try {
    runs = await getAnalysisRuns({ sortBy: "created_at", sortOrder: "desc" });
  } catch (error) {
    loadError =
      error instanceof ApiError
        ? error.message
        : "Saved analysis runs could not be loaded.";
  }

  return (
    <>
      <PageHeader
        title="History"
        description="Results you have saved, newest first."
        action={
          <Link href={`/analyze?dataset=${encodeURIComponent(datasetName)}`}>
            <Button>New analysis</Button>
          </Link>
        }
      />

      {loadError ? (
        <ErrorState
          title="Saved results are unavailable"
          description={`${loadError} Saving results needs the database, which is not switched on right now.`}
        />
      ) : runs.length === 0 ? (
        <EmptyState
          title="Nothing saved yet"
          description="Check your skills, then save the result to track how your match improves as you learn."
          action={
            <Link href={`/analyze?dataset=${encodeURIComponent(datasetName)}`}>
              <Button>Check my skills</Button>
            </Link>
          }
        />
      ) : (
        <Card>
          <ul className="divide-y divide-border">
            {runs.map((run) => (
              <AnalysisRunRow key={run.id} run={run} />
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}
