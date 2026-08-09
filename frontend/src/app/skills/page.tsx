import { DemandBarChart } from "@/components/charts/DemandBarChart";
import { PageHeader, Section } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { TableDisclosure } from "@/components/ui/TableDisclosure";
import { getMarketInsights } from "@/lib/api/endpoints";
import type {
  CompanyDemand,
  LocationDemand,
  RoleSkillImportance,
} from "@/lib/api/types";
import { resolveDataset } from "@/lib/datasets";
import { formatCount, formatDatasetLabel, formatSkill } from "@/lib/format";

const locationColumns: Column<LocationDemand>[] = [
  { key: "location", header: "Location", render: (row) => row.location },
  {
    key: "job_count",
    header: "Postings",
    align: "right",
    render: (row) => formatCount(row.job_count),
  },
];

const companyColumns: Column<CompanyDemand>[] = [
  { key: "company", header: "Company", render: (row) => row.company },
  {
    key: "job_count",
    header: "Postings",
    align: "right",
    render: (row) => formatCount(row.job_count),
  },
];

const importanceColumns: Column<RoleSkillImportance>[] = [
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

export default async function SkillsPage({ searchParams }: PageProps<"/skills">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);
  const insights = await getMarketInsights({ datasetName, topN: 12 });

  const skillDemandData = insights.skill_demand.map((item) => ({
    label: formatSkill(item.skill),
    value: item.job_count,
  }));

  const roleDistributionData = insights.role_distribution.map((item) => ({
    label: item.role_category,
    value: item.job_count,
  }));

  return (
    <>
      <PageHeader
        title="Skills & Market"
        description="What this job market is hiring for, independent of any candidate profile."
        action={
          <Badge tone="neutral">
            {formatDatasetLabel(insights.dataset_name)} ·{" "}
            {formatCount(insights.jobs_analyzed)} postings
          </Badge>
        }
      />

      {/* items-start keeps each card at its natural height when the two charts
          have different row counts. */}
      <div className="grid items-start gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Skill demand"
            description="How many postings in this snapshot ask for each skill."
          />
          <CardBody>
            <DemandBarChart data={skillDemandData} valueLabel="postings" />
          </CardBody>
          <TableDisclosure>
            <DataTable
              columns={[
                { key: "label", header: "Skill", render: (row) => row.label },
                {
                  key: "value",
                  header: "Postings",
                  align: "right",
                  render: (row) => formatCount(row.value),
                },
              ]}
              rows={skillDemandData}
              getRowKey={(row) => row.label}
              caption="Skill demand by posting count"
            />
          </TableDisclosure>
        </Card>

        <Card>
          <CardHeader
            title="Role distribution"
            description="How the postings break down across role categories."
          />
          <CardBody>
            <DemandBarChart
              data={roleDistributionData}
              valueLabel="postings"
              categoryWidth={130}
            />
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
              rows={roleDistributionData}
              getRowKey={(row) => row.label}
              caption="Postings by role category"
            />
          </TableDisclosure>
        </Card>
      </div>

      <Section
        title="Role-specific skill importance"
        description="Skills ranked by how often a role asks for them and how much that role weights them."
      >
        <Card>
          <DataTable
            columns={importanceColumns}
            rows={insights.role_skill_importance}
            getRowKey={(row) => `${row.role_category}-${row.skill}`}
            caption="Skill importance weighted by role"
            emptyMessage="No role-specific skill weights were produced for this dataset."
          />
        </Card>
      </Section>

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Where the jobs are"
            description="Posting concentration by location."
          />
          <DataTable
            columns={locationColumns}
            rows={insights.jobs_by_location}
            getRowKey={(row) => row.location}
            caption="Postings by location"
          />
        </Card>

        <Card>
          <CardHeader
            title="Top hiring companies"
            description="Employers with the most postings in this snapshot."
          />
          <DataTable
            columns={companyColumns}
            rows={insights.top_companies}
            getRowKey={(row) => row.company}
            caption="Postings by company"
          />
        </Card>
      </div>

      <p className="text-sm text-text-subtle">
        Demand is measured across the current snapshot only. JobLens does not
        retain historical snapshots, so these counts are not a trend over time.
      </p>
    </>
  );
}
