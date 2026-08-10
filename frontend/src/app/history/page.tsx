import Link from "next/link";
import { Suspense } from "react";

import { AnalysisRunRow } from "@/components/domain/AnalysisRunRow";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/ui/States";
import { ApiError } from "@/lib/api/client";
import { getAnalysisRuns } from "@/lib/api/endpoints";
import type { AnalysisRun } from "@/lib/api/types";
import { resolveDataset } from "@/lib/datasets";

async function SavedRuns({ datasetName }: { datasetName: string }) {
  let runs: AnalysisRun[] = [];
  let loadError: string | null = null;

  try {
    runs = await getAnalysisRuns({ sortBy: "created_at", sortOrder: "desc" });
  } catch (error) {
    loadError =
      error instanceof ApiError
        ? error.message
        : "Saved results could not be loaded.";
  }

  if (loadError) {
    return (
      <ErrorState
        title="Saved results are unavailable"
        description={`${loadError} Saving results needs the database, which is not switched on right now.`}
      />
    );
  }

  if (runs.length === 0) {
    return (
      <EmptyState
        title="Nothing saved yet"
        description="Check your skills, then save the result to track how your match improves as you learn."
        action={
          <Link href={`/analyze?dataset=${encodeURIComponent(datasetName)}`}>
            <Button>Check my skills</Button>
          </Link>
        }
      />
    );
  }

  return (
    <Card>
      <ul className="divide-y divide-border">
        {runs.map((run) => (
          <AnalysisRunRow key={run.id} run={run} />
        ))}
      </ul>
    </Card>
  );
}

export default async function HistoryPage({
  searchParams,
}: PageProps<"/history">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="History"
        description="Results you have saved, newest first."
        action={
          <Link href={`/analyze?dataset=${encodeURIComponent(datasetName)}`}>
            <Button>Check my skills</Button>
          </Link>
        }
      />

      <Suspense key={datasetName} fallback={<CardSkeleton rows={6} />}>
        <SavedRuns datasetName={datasetName} />
      </Suspense>
    </>
  );
}
