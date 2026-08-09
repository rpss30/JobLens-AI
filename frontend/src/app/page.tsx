import Link from "next/link";

import { OverviewContent } from "@/components/domain/OverviewContent";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { getFilterOptions } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";
import { formatDatasetLabel } from "@/lib/format";

export default async function OverviewPage({ searchParams }: PageProps<"/">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);
  const filterOptions = await getFilterOptions(datasetName);

  const refreshedNote = filterOptions.summary.refreshed_date
    ? ` · refreshed ${filterOptions.summary.refreshed_date}`
    : "";

  return (
    <>
      <PageHeader
        title="Overview"
        description={`${formatDatasetLabel(filterOptions.dataset_name)}${refreshedNote}`}
        action={
          <Link href={`/analyze?dataset=${encodeURIComponent(datasetName)}`}>
            <Button>New analysis</Button>
          </Link>
        }
      />

      <OverviewContent
        datasetName={datasetName}
        summary={filterOptions.summary}
      />
    </>
  );
}
