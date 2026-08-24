import { Suspense } from "react";

import { DatasetRow } from "@/components/domain/DatasetRow";
import { DatasetUploadForm } from "@/components/domain/DatasetUploadForm";
import { PageHeader, Section } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { CardSkeleton, EmptyState, ErrorState } from "@/components/ui/States";
import { ApiError } from "@/lib/api/client";
import { getDatasets } from "@/lib/api/endpoints";
import type { DatasetSummary } from "@/lib/api/types";

// This page mirrors live database state, so it must not be prerendered.
export const dynamic = "force-dynamic";

async function SavedDatasets() {
  let datasets: DatasetSummary[] = [];
  let loadError: string | null = null;

  try {
    datasets = await getDatasets();
  } catch (error) {
    loadError =
      error instanceof ApiError
        ? error.message
        : "Saved datasets could not be loaded.";
  }

  if (loadError) {
    return (
      <ErrorState
        title="Your uploads are unavailable"
        description={`${loadError} Uploading needs the database, which is not switched on right now.`}
      />
    );
  }

  if (datasets.length === 0) {
    return (
      <EmptyState
        title="Nothing uploaded yet"
        description="Upload a spreadsheet of jobs above to check your skills against your own list."
      />
    );
  }

  return (
    <Card>
      <ul className="divide-y divide-border">
        {datasets.map((dataset) => (
          <DatasetRow key={dataset.name} dataset={dataset} />
        ))}
      </ul>
    </Card>
  );
}

export default function DatasetsPage() {
  return (
    <>
      <PageHeader
        title="Datasets"
        description="Bring your own job postings, or manage the ones you have already added."
      />

      <div className="animate-section-in">
        <DatasetUploadForm />
      </div>

      <div
        className="animate-section-in"
        style={{ animationDelay: "90ms" }}
      >
        <Section
          title="Saved datasets"
          description="Sets you upload can be renamed or deleted. The ones that ship with JobLens are read-only."
        >
          <Suspense fallback={<CardSkeleton rows={5} />}>
            <SavedDatasets />
          </Suspense>
        </Section>
      </div>
    </>
  );
}
