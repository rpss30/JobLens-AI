import { Suspense } from "react";

import { layoutTreemap } from "@/components/charts/RoleTreemap";
import { TreemapTile } from "@/components/charts/TreemapTile";
import {
  TotalPostingsBadge,
  TotalPostingsBadgeSkeleton,
} from "@/components/domain/TotalPostingsBadge";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { CardSkeleton } from "@/components/ui/States";
import { TableDisclosure } from "@/components/ui/TableDisclosure";
import { getMarketInsights } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";
import { formatCount } from "@/lib/format";

async function RoleDistribution({ datasetName }: { datasetName: string }) {
  const insights = await getMarketInsights({ datasetName, topN: 25 });

  const rows = insights.role_distribution.map((item) => ({
    label: item.role_category,
    value: item.job_count,
    share:
      insights.jobs_analyzed > 0 ? item.job_count / insights.jobs_analyzed : 0,
  }));

  const tiles = layoutTreemap(rows);
  const shareOf = new Map(rows.map((row) => [row.label, row.share]));

  if (tiles.length === 0) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-text-muted">
            No role categories were produced for this dataset.
          </p>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardBody className="p-4 sm:p-5">
        <div className="relative h-[26rem] w-full sm:h-[32rem]">
          {tiles.map((tile) => {
            const share = shareOf.get(tile.label) ?? 0;

            return (
              <div
                key={tile.label}
                className="absolute p-1"
                style={{
                  left: `${tile.x}%`,
                  top: `${tile.y}%`,
                  width: `${tile.width}%`,
                  height: `${tile.height}%`,
                }}
              >
                <TreemapTile
                  label={tile.label}
                  value={tile.value}
                  share={share}
                  top={tile.y}
                  step={tile.step}
                  // Height is what limits stacked content, not area: a wide,
                  // short tile has plenty of area and no room.
                  showIcon={tile.height >= 30}
                  showShare={tile.height >= 22}
                  isLargest={tile === tiles[0]}
                />
              </div>
            );
          })}
        </div>
      </CardBody>

      <TableDisclosure label="View as table">
        <DataTable
          columns={[
            { key: "label", header: "Role", render: (row) => row.label },
            {
              key: "value",
              header: "Postings",
              align: "right",
              render: (row) => formatCount(row.value),
            },
            {
              key: "share",
              header: "Share",
              align: "right",
              render: (row) => `${Math.round(row.share * 100)}%`,
            },
          ]}
          rows={rows}
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
        action={
          <Suspense fallback={<TotalPostingsBadgeSkeleton />}>
            <TotalPostingsBadge datasetName={datasetName} />
          </Suspense>
        }
      />

      <Suspense key={datasetName} fallback={<CardSkeleton rows={10} />}>
        <RoleDistribution datasetName={datasetName} />
      </Suspense>
    </>
  );
}
