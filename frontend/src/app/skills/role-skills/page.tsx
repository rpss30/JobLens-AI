import { Suspense } from "react";

import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { CardSkeleton } from "@/components/ui/States";
import { getMarketInsights } from "@/lib/api/endpoints";
import type { RoleSkillImportance } from "@/lib/api/types";
import { resolveDataset } from "@/lib/datasets";
import { formatCount, formatSkill } from "@/lib/format";

const columns: Column<RoleSkillImportance>[] = [
  {
    key: "skill",
    header: "Skill",
    render: (row) => (
      <span className="font-medium">{formatSkill(row.skill)}</span>
    ),
  },
  { key: "role_category", header: "Role", render: (row) => row.role_category },
  {
    key: "job_count",
    header: "Postings",
    align: "right",
    render: (row) => formatCount(row.job_count),
  },
  {
    key: "role_weight",
    header: "Weight",
    align: "right",
    render: (row) => row.role_weight,
  },
  {
    key: "weighted_importance",
    header: "Importance",
    align: "right",
    render: (row) => row.weighted_importance.toFixed(0),
  },
];

async function RoleSkills({ datasetName }: { datasetName: string }) {
  const insights = await getMarketInsights({ datasetName, topN: 12 });

  return (
    <Card>
      <DataTable
        columns={columns}
        rows={insights.role_skill_importance}
        getRowKey={(row) => `${row.role_category}-${row.skill}`}
        caption="Skill importance weighted by role"
        minWidthClassName="min-w-[38rem]"
        emptyMessage="No role-specific skill weights were produced for this dataset."
      />
    </Card>
  );
}

export default async function RoleSkillsPage({
  searchParams,
}: PageProps<"/skills/role-skills">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Role Specific Skills"
        description="Skills ranked by how often a role asks for them and how much that role weights them."
      />
      <Suspense key={datasetName} fallback={<CardSkeleton rows={8} />}>
        <RoleSkills datasetName={datasetName} />
      </Suspense>
    </>
  );
}
