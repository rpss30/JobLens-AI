import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { CardSkeleton } from "@/components/ui/States";
import { getMarketInsights } from "@/lib/api/endpoints";
import type { LocationDemand } from "@/lib/api/types";
import { resolveDataset } from "@/lib/datasets";
import { formatCount } from "@/lib/format";

const columns: Column<LocationDemand>[] = [
  { key: "location", header: "Location", render: (row) => row.location },
  {
    key: "job_count",
    header: "Postings",
    align: "right",
    render: (row) => formatCount(row.job_count),
  },
];

async function JobLocations({ datasetName }: { datasetName: string }) {
  const insights = await getMarketInsights({ datasetName, topN: 12 });

  return (
    <Card>
      <DataTable
        columns={columns}
        rows={insights.jobs_by_location}
        getRowKey={(row) => row.location}
        caption="Postings by location"
      />
    </Card>
  );
}

export default async function JobLocationsPage({
  searchParams,
}: PageProps<"/skills/locations">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Job Locations"
        description="Posting concentration by location."
      />
      <Suspense key={datasetName} fallback={<CardSkeleton rows={8} />}>
        <JobLocations datasetName={datasetName} />
      </Suspense>
    </>
  );
}
