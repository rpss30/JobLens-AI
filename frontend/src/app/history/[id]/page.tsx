import Link from "next/link";
import { notFound } from "next/navigation";

import { PageHeader, Section } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatTile } from "@/components/ui/StatTile";
import { ApiError } from "@/lib/api/client";
import { getAnalysisRun } from "@/lib/api/endpoints";
import { formatCount, formatDate, formatPercent, formatSkill } from "@/lib/format";

type SavedRoleScore = Record<string, unknown>;

function readText(row: SavedRoleScore, key: string): string {
  const value = row[key];

  return value === null || value === undefined ? "—" : String(value);
}

function readNumber(row: SavedRoleScore, key: string): string {
  const value = Number(row[key]);

  return Number.isFinite(value) ? value.toFixed(1) : "—";
}

const roleScoreColumns: Column<SavedRoleScore>[] = [
  {
    key: "role_category",
    header: "Role",
    render: (row) => (
      <span className="font-medium">{readText(row, "role_category")}</span>
    ),
  },
  {
    key: "weighted_match_score",
    header: "Weighted fit",
    align: "right",
    render: (row) => `${readNumber(row, "weighted_match_score")}%`,
  },
  {
    key: "unweighted_match_score",
    header: "Unweighted fit",
    align: "right",
    render: (row) => `${readNumber(row, "unweighted_match_score")}%`,
  },
  {
    key: "sample_size",
    header: "Postings",
    align: "right",
    render: (row) => readText(row, "sample_size"),
  },
  {
    key: "sample_confidence",
    header: "Confidence",
    align: "right",
    render: (row) => readText(row, "sample_confidence"),
  },
];

function ChipList({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-text-subtle">
        {label}
      </p>
      {items.length === 0 ? (
        <p className="mt-1.5 text-sm text-text-muted">None recorded.</p>
      ) : (
        <ul className="mt-1.5 flex flex-wrap gap-1.5">
          {items.map((item) => (
            <li key={item}>
              <Badge tone="neutral">{formatSkill(item)}</Badge>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default async function AnalysisRunPage({
  params,
}: PageProps<"/history/[id]">) {
  const { id } = await params;
  const analysisRunId = Number(id);

  if (!Number.isInteger(analysisRunId) || analysisRunId < 1) {
    notFound();
  }

  let run;

  try {
    run = await getAnalysisRun(analysisRunId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }

    throw error;
  }

  const savedRoleScores = (run.role_scores ?? []) as SavedRoleScore[];

  return (
    <>
      <PageHeader
        title={run.name}
        description={`Saved ${formatDate(run.created_at)} against ${run.dataset_name}`}
        action={
          <Link
            href="/history"
            className="text-sm font-medium text-accent hover:underline"
          >
            Back to history
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Best-fit role" value={run.best_role ?? "No match"} />
        <StatTile
          label="Role skill fit"
          value={
            run.weighted_match_score === null
              ? "N/A"
              : formatPercent(run.weighted_match_score)
          }
          emphasis
        />
        <StatTile
          label="Top skill gap"
          value={
            run.top_missing_skill ? formatSkill(run.top_missing_skill) : "None"
          }
        />
        <StatTile
          label="Jobs analyzed"
          value={formatCount(run.jobs_analyzed)}
        />
      </div>

      <Card>
        <CardHeader
          title="Search scope"
          description="The filters and profile this run was scored against."
        />
        <CardBody className="space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-text-subtle">
                Location
              </p>
              <p className="mt-1 text-sm text-text">{run.location}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-text-subtle">
                Experience level
              </p>
              <p className="mt-1 text-sm text-text">{run.experience_level}</p>
            </div>
          </div>

          <ChipList label="Target roles" items={run.target_roles} />
          <ChipList label="Profile skills" items={run.current_skills} />
          <ChipList label="Recommended skills" items={run.recommended_skills} />
        </CardBody>
      </Card>

      <Section
        title="Saved role scores"
        description="The role breakdown exactly as it was scored when this run was saved."
      >
        <Card>
          <DataTable
            columns={roleScoreColumns}
            rows={savedRoleScores}
            getRowKey={(row, index) => `${readText(row, "role_category")}-${index}`}
            caption="Role scores recorded with this analysis run"
            minWidthClassName="min-w-[38rem]"
            emptyMessage="No role scores were stored with this run."
          />
        </Card>
      </Section>
    </>
  );
}
