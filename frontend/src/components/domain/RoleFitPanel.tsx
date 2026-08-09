import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ScoreBar } from "@/components/ui/ScoreBar";
import type { RoleScore } from "@/lib/api/types";

// Labels come from get_sample_confidence in the matching engine.
const confidenceTones: Record<string, BadgeTone> = {
  Strong: "positive",
  Moderate: "accent",
  Limited: "warning",
  Insufficient: "danger",
};

// Plain-language stand-ins for the matching engine's confidence labels.
const confidenceLabels: Record<string, string> = {
  Strong: "Based on plenty of jobs",
  Moderate: "Based on a fair number of jobs",
  Limited: "Based on only a few jobs",
  Insufficient: "Not enough jobs to judge",
};

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  return (
    <Badge tone={confidenceTones[confidence] ?? "neutral"}>
      {confidenceLabels[confidence] ?? confidence}
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
        title="How you match each type of role"
        description="Skills that show up in more job ads count for more, so this reflects what employers actually ask for."
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
                  {role.sample_size} {role.sample_size === 1 ? "job" : "jobs"} in
                  this category
                </span>
              </div>
            </div>
          ))
        )}
      </CardBody>
    </Card>
  );
}
