import { PageHeader } from "@/components/layout/PageHeader";
import { AnalyzeForm } from "@/components/domain/AnalyzeForm";
import { Badge } from "@/components/ui/Badge";
import { getFilterOptions } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";
import { formatCount } from "@/lib/format";

export default async function AnalyzePage({ searchParams }: PageProps<"/analyze">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);
  const filterOptions = await getFilterOptions(datasetName);
  const { summary } = filterOptions;

  return (
    <>
      <PageHeader
        title="Analyze"
        description="Tell us what you can do, and we will show you which jobs you fit and what you are missing."
        action={
          <Badge tone="neutral">
            Comparing against {formatCount(summary.job_count)} jobs
          </Badge>
        }
      />

      <AnalyzeForm filterOptions={filterOptions} datasetName={datasetName} />
    </>
  );
}
