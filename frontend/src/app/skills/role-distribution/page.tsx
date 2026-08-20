import { Suspense } from "react";

import { RoleDistribution } from "@/components/charts/RoleDistribution";
import type { RoleGroup } from "@/components/charts/RoleSkillsPanel";
import {
  TotalPostingsBadge,
  TotalPostingsBadgeSkeleton,
} from "@/components/domain/TotalPostingsBadge";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { CardSkeleton } from "@/components/ui/States";
import { getMarketInsights } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";

async function RoleDistributionSection({
  datasetName,
  header,
}: {
  datasetName: string;
  header: React.ReactNode;
}) {
  const insights = await getMarketInsights({ datasetName, topN: 6 });

  const rows = insights.role_distribution.map((item) => ({
    label: item.role_category,
    value: item.job_count,
    share:
      insights.jobs_analyzed > 0 ? item.job_count / insights.jobs_analyzed : 0,
  }));

  const byRole = new Map<string, RoleGroup>();

  for (const row of insights.role_skill_importance) {
    const group = byRole.get(row.role_category) ?? {
      roleCategory: row.role_category,
      rolePostings: row.role_job_count,
      skills: [],
    };

    group.skills.push(row);
    byRole.set(row.role_category, group);
  }

  const roles = [...byRole.values()];

  if (rows.length === 0) {
    // The heading is handed to the chart, so it has to be drawn here too
    // rather than left out with the chart that never arrived.
    return (
      <>
        {header}
        <Card>
          <CardBody>
            <p className="text-sm text-text-muted">
              No role categories were produced for this dataset.
            </p>
          </CardBody>
        </Card>
      </>
    );
  }

  return (
    <RoleDistribution
      rows={rows}
      roles={roles}
      datasetName={datasetName}
      header={header}
    />
  );
}

export default async function RoleDistributionPage({
  searchParams,
}: PageProps<"/skills/role-distribution">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  const header = (
    <PageHeader
      title="Role Distribution"
      description="How the postings break down across role categories."
      action={
        <Suspense fallback={<TotalPostingsBadgeSkeleton />}>
          <TotalPostingsBadge datasetName={datasetName} />
        </Suspense>
      }
    />
  );

  return (
    <Suspense
      key={datasetName}
      fallback={
        <>
          {header}
          <CardSkeleton rows={12} />
        </>
      }
    >
      <RoleDistributionSection datasetName={datasetName} header={header} />
    </Suspense>
  );
}
