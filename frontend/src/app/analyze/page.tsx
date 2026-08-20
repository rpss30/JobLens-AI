import { Suspense } from "react";

import {
  ANALYZE_HEADING,
  AnalyzeView,
} from "@/components/domain/AnalyzeView";
import { PageHeader } from "@/components/layout/PageHeader";
import { CardSkeleton } from "@/components/ui/States";
import { getFilterOptions } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";

async function AnalyzeSection({ datasetName }: { datasetName: string }) {
  const filterOptions = await getFilterOptions(datasetName);

  return <AnalyzeView filterOptions={filterOptions} datasetName={datasetName} />;
}

export default async function AnalyzePage({ searchParams }: PageProps<"/analyze">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    // The heading depends on whether a result exists, which only the client
    // knows, so it is drawn inside. The fallback carries the form's heading
    // so it does not arrive late.
    <Suspense
      key={datasetName}
      fallback={
        <>
          <PageHeader
            title={ANALYZE_HEADING.title}
            description={ANALYZE_HEADING.description}
          />
          <CardSkeleton rows={8} />
        </>
      }
    >
      <AnalyzeSection datasetName={datasetName} />
    </Suspense>
  );
}
