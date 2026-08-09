import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/DataTable";
import type { RecommendedSkill } from "@/lib/api/types";
import { formatCount, formatSkill } from "@/lib/format";

const columns: Column<RecommendedSkill>[] = [
  {
    key: "skill",
    header: "Skill",
    render: (row) => (
      <span className="font-medium">{formatSkill(row.skill)}</span>
    ),
  },
  {
    key: "job_count",
    header: "Jobs asking for it",
    align: "right",
    render: (row) => formatCount(row.job_count),
  },
];

export function SkillGapPanel({ skills }: { skills: RecommendedSkill[] }) {
  return (
    <Card>
      <CardHeader
        title="Skills worth learning next"
        description="Skills you are missing, with the ones employers ask for most at the top."
      />
      <CardBody className="px-0 py-0">
        <DataTable
          columns={columns}
          rows={skills}
          getRowKey={(row) => row.skill}
          caption="Skills to learn next"
          emptyMessage="Nothing major is missing for this search."
        />
      </CardBody>
    </Card>
  );
}
