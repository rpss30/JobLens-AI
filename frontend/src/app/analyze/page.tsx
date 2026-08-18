import { Suspense } from "react";

import { AnalyzeForm } from "@/components/domain/AnalyzeForm";
import { PageHeader } from "@/components/layout/PageHeader";
import { CardSkeleton } from "@/components/ui/States";
import { getFilterOptions } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";

async function AnalyzeFormSection({ datasetName }: { datasetName: string }) {
  const filterOptions = await getFilterOptions(datasetName);

  return <AnalyzeForm filterOptions={filterOptions} datasetName={datasetName} />;
}

export default async function AnalyzePage({ searchParams }: PageProps<"/analyze">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Analyze"
        description="Tell us what you can do, and we will show you which jobs you fit and what you are missing."
      />

      <Suspense
        key={datasetName}
        fallback={<CardSkeleton rows={8} />}
      >
        <AnalyzeFormSection datasetName={datasetName} />
      </Suspense>
    </>
  );
}
