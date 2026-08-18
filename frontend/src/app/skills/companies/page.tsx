import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { CardSkeleton } from "@/components/ui/States";
import { getMarketInsights } from "@/lib/api/endpoints";
import type { CompanyDemand } from "@/lib/api/types";
import { resolveDataset } from "@/lib/datasets";
import { formatCount } from "@/lib/format";

const columns: Column<CompanyDemand>[] = [
  { key: "company", header: "Company", render: (row) => row.company },
  {
    key: "job_count",
    header: "Postings",
    align: "right",
    render: (row) => formatCount(row.job_count),
  },
];

async function TopCompanies({ datasetName }: { datasetName: string }) {
  const insights = await getMarketInsights({ datasetName, topN: 12 });

  return (
    <Card>
      <DataTable
        columns={columns}
        rows={insights.top_companies}
        getRowKey={(row) => row.company}
        caption="Postings by company"
      />
    </Card>
  );
}

export default async function TopCompaniesPage({
  searchParams,
}: PageProps<"/skills/companies">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Top Hiring Companies"
        description="Employers with the most postings in this snapshot."
      />
      <Suspense key={datasetName} fallback={<CardSkeleton rows={8} />}>
        <TopCompanies datasetName={datasetName} />
      </Suspense>
    </>
  );
}
