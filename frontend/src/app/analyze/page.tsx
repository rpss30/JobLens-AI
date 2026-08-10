import { Suspense } from "react";

import { AnalyzeForm } from "@/components/domain/AnalyzeForm";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { CardSkeleton } from "@/components/ui/States";
import { getFilterOptions } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";
import { formatCount } from "@/lib/format";

async function AnalyzeFormSection({ datasetName }: { datasetName: string }) {
  const filterOptions = await getFilterOptions(datasetName);

  return (
    <>
      <Badge tone="neutral">
        Comparing against {formatCount(filterOptions.summary.job_count)} jobs
      </Badge>

      <AnalyzeForm filterOptions={filterOptions} datasetName={datasetName} />
    </>
  );
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
        fallback={
          <div className="grid gap-6 lg:grid-cols-2">
            <CardSkeleton rows={6} />
            <CardSkeleton rows={6} />
          </div>
        }
      >
        <AnalyzeFormSection datasetName={datasetName} />
      </Suspense>
    </>
  );
}
