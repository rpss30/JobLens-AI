import { Suspense } from "react";

import {
  RoleSkillsExplorer,
  type RoleGroup,
} from "@/components/charts/RoleSkillsExplorer";
import {
  TotalPostingsBadge,
  TotalPostingsBadgeSkeleton,
} from "@/components/domain/TotalPostingsBadge";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { CardSkeleton } from "@/components/ui/States";
import { getMarketInsights } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";

async function RoleSkills({ datasetName }: { datasetName: string }) {
  const insights = await getMarketInsights({ datasetName, topN: 6 });

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

  // Busiest role first, so the panel opens on the one most postings sit in.
  const roles = [...byRole.values()].sort(
    (first, second) => second.rolePostings - first.rolePostings,
  );

  if (roles.length === 0) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-text-muted">
            No role-specific skills were produced for this dataset.
          </p>
        </CardBody>
      </Card>
    );
  }

  return <RoleSkillsExplorer roles={roles} />;
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
        description="The skills employers ask for most often in each role category."
        action={
          <Suspense fallback={<TotalPostingsBadgeSkeleton />}>
            <TotalPostingsBadge datasetName={datasetName} />
          </Suspense>
        }
      />

      <Suspense key={datasetName} fallback={<CardSkeleton rows={10} />}>
        <RoleSkills datasetName={datasetName} />
      </Suspense>
    </>
  );
}
