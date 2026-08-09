import { DatasetRow } from "@/components/domain/DatasetRow";
import { DatasetUploadForm } from "@/components/domain/DatasetUploadForm";
import { PageHeader, Section } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { ApiError } from "@/lib/api/client";
import { getDatasets } from "@/lib/api/endpoints";
import type { DatasetSummary } from "@/lib/api/types";

// This page mirrors live PostgreSQL state, so it must not be prerendered.
export const dynamic = "force-dynamic";

export default async function DatasetsPage() {
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

  return (
    <>
      <PageHeader
        title="Datasets"
        description="Upload your own job postings and manage the datasets saved to PostgreSQL."
      />

      <DatasetUploadForm />

      <Section
        title="Saved datasets"
        description="Uploaded CSV datasets can be renamed or deleted. Bundled samples are locked."
      >
        {loadError ? (
          <ErrorState
            title="Datasets are unavailable"
            description={`${loadError} Saved datasets need PostgreSQL, which is optional for local development.`}
          />
        ) : datasets.length === 0 ? (
          <EmptyState
            title="No saved datasets"
            description="Upload a jobs CSV above to analyze your own postings alongside the bundled datasets."
          />
        ) : (
          <Card>
            <ul className="divide-y divide-border">
              {datasets.map((dataset) => (
                <DatasetRow key={dataset.name} dataset={dataset} />
              ))}
            </ul>
          </Card>
        )}
      </Section>
    </>
  );
}
