import { Suspense } from "react";

import { DemandBarChart } from "@/components/charts/DemandBarChart";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { CardSkeleton } from "@/components/ui/States";
import { TableDisclosure } from "@/components/ui/TableDisclosure";
import { getMarketInsights } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";
import { formatCount } from "@/lib/format";

async function RoleDistribution({ datasetName }: { datasetName: string }) {
  const insights = await getMarketInsights({ datasetName, topN: 12 });
  const data = insights.role_distribution.map((item) => ({
    label: item.role_category,
    value: item.job_count,
  }));

  return (
    <Card>
      <CardBody>
        <DemandBarChart data={data} valueLabel="postings" categoryWidth={130} />
      </CardBody>
      <TableDisclosure>
        <DataTable
          columns={[
            { key: "label", header: "Role", render: (row) => row.label },
            {
              key: "value",
              header: "Postings",
              align: "right",
              render: (row) => formatCount(row.value),
            },
          ]}
          rows={data}
          getRowKey={(row) => row.label}
          caption="Postings by role category"
        />
      </TableDisclosure>
    </Card>
  );
}

export default async function RoleDistributionPage({
  searchParams,
}: PageProps<"/skills/role-distribution">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Role Distribution"
        description="How the postings break down across role categories."
      />
      <Suspense key={datasetName} fallback={<CardSkeleton rows={8} />}>
        <RoleDistribution datasetName={datasetName} />
      </Suspense>
    </>
  );
}
