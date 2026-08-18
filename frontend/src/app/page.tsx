import { Suspense } from "react";

import { OverviewContent } from "@/components/domain/OverviewContent";
import { PageHeader } from "@/components/layout/PageHeader";
import { CardSkeleton } from "@/components/ui/States";
import { getFilterOptions } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";

async function OverviewSection({ datasetName }: { datasetName: string }) {
  const filterOptions = await getFilterOptions(datasetName);

  return (
    <OverviewContent
      datasetName={datasetName}
      summary={filterOptions.summary}
    />
  );
}

export default async function OverviewPage({ searchParams }: PageProps<"/">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Overview"
        description="Your results at a glance, based on real job postings"
      />

      <Suspense key={datasetName} fallback={<CardSkeleton rows={6} />}>
        <OverviewSection datasetName={datasetName} />
      </Suspense>
    </>
  );
}
