import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ScoreBar } from "@/components/ui/ScoreBar";
import type { RoleScore } from "@/lib/api/types";

const confidenceTones: Record<string, BadgeTone> = {
  High: "positive",
  Moderate: "accent",
  Limited: "warning",
};

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  return (
    <Badge tone={confidenceTones[confidence] ?? "neutral"}>
      {confidence} confidence
    </Badge>
  );
}

export function RoleFitPanel({ roleScores }: { roleScores: RoleScore[] }) {
  const rankedRoles = [...roleScores]
    .sort((first, second) => second.weighted_match_score - first.weighted_match_score)
    .slice(0, 6);

  return (
    <Card>
      <CardHeader
        title="Role match"
        description="Weighted skill fit per role category, using role-specific skill importance."
      />
      <CardBody className="space-y-5">
        {rankedRoles.length === 0 ? (
          <p className="text-sm text-text-muted">
            No role scores were produced for this search.
          </p>
        ) : (
          rankedRoles.map((role) => (
            <div key={role.role_category} className="space-y-2">
              <ScoreBar
                label={role.role_category}
                value={role.weighted_match_score}
              />
              <div className="flex flex-wrap items-center gap-2">
                <ConfidenceBadge confidence={role.sample_confidence} />
                <span className="text-xs text-text-subtle">
                  {role.representative_job_count} representative of{" "}
                  {role.sample_size} postings
                </span>
              </div>
            </div>
          ))
        )}
      </CardBody>
    </Card>
  );
}
