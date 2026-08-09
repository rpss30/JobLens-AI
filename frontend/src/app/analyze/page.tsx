import { PageHeader } from "@/components/layout/PageHeader";
import { AnalyzeForm } from "@/components/domain/AnalyzeForm";
import { Badge } from "@/components/ui/Badge";
import { getFilterOptions } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";
import { formatCount, formatDatasetLabel } from "@/lib/format";

export default async function AnalyzePage({ searchParams }: PageProps<"/analyze">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);
  const filterOptions = await getFilterOptions(datasetName);
  const { summary } = filterOptions;

  return (
    <>
      <PageHeader
        title="Analyze"
        description="Score your skills against real postings to see role fit, skill gaps, and the jobs that match."
        action={
          <Badge tone="neutral">
            {formatDatasetLabel(filterOptions.dataset_name)} ·{" "}
            {formatCount(summary.job_count)} postings
          </Badge>
        }
      />

      <AnalyzeForm filterOptions={filterOptions} datasetName={datasetName} />
    </>
  );
}
