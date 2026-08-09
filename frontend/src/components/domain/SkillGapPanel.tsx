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
    header: "Postings",
    align: "right",
    render: (row) => formatCount(row.job_count),
  },
  {
    key: "avg_weight",
    header: "Avg weight",
    align: "right",
    render: (row) => row.avg_weight.toFixed(1),
  },
];

export function SkillGapPanel({ skills }: { skills: RecommendedSkill[] }) {
  return (
    <Card>
      <CardHeader
        title="Highest-impact skill gaps"
        description="Missing skills ranked by how often they appear and how much each role weights them."
      />
      <CardBody className="px-0 py-0">
        <DataTable
          columns={columns}
          rows={skills}
          getRowKey={(row) => row.skill}
          caption="Recommended skills to learn"
          emptyMessage="No major skill gaps were found for this search."
        />
      </CardBody>
    </Card>
  );
}
