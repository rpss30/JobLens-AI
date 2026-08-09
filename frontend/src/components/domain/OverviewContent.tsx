"use client";

import Link from "next/link";

import { JobMatchCard } from "@/components/domain/JobMatchCard";
import { RoleFitPanel } from "@/components/domain/RoleFitPanel";
import { SaveAnalysisButton } from "@/components/domain/SaveAnalysisButton";
import { SkillGapPanel } from "@/components/domain/SkillGapPanel";
import { Section } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { StatTile } from "@/components/ui/StatTile";
import { EmptyState } from "@/components/ui/States";
import { useAnalysis } from "@/context/AnalysisContext";
import type { DatasetSnapshotSummary } from "@/lib/api/types";
import { formatCount, formatPercent, formatSkill } from "@/lib/format";

interface OverviewContentProps {
  datasetName: string;
  summary: DatasetSnapshotSummary;
}

export function OverviewContent({
  datasetName,
  summary,
}: OverviewContentProps) {
  const { analysis } = useAnalysis();
  const analyzeHref = `/analyze?dataset=${encodeURIComponent(datasetName)}`;

  if (!analysis) {
    return (
      <EmptyState
        title="No analysis yet"
        description={`This dataset holds ${formatCount(summary.job_count)} postings from ${formatCount(summary.company_count)} employers across ${formatCount(summary.location_count)} locations. Run an analysis to see how your skills score against it.`}
        action={
          <Link href={analyzeHref}>
            <Button>Run your first analysis</Button>
          </Link>
        }
      />
    );
  }

  const { response, request } = analysis;
  const topJobs = response.top_matching_jobs.slice(0, 3);

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Best-fit role"
          value={response.best_role}
          hint={`Scored across ${formatCount(response.jobs_analyzed)} postings`}
        />
        <StatTile
          label="Role skill fit"
          value={formatPercent(response.weighted_match_score)}
          emphasis
        />
        <StatTile
          label="Top skill gap"
          value={formatSkill(response.top_missing_skill)}
        />
        <StatTile
          label="Profile skills"
          value={formatCount(
            response.resume_analysis?.combined_skills.length ??
              request.current_skills.length,
          )}
          hint={response.resume_analysis ? "Includes resume-extracted skills" : undefined}
        />
      </div>

      <SaveAnalysisButton />

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <RoleFitPanel roleScores={response.role_scores} />
        <SkillGapPanel skills={response.recommended_skills} />
      </div>

      <Section
        title="Strongest job matches"
        description="Postings where your current skills overlap most with what the role requires."
        action={
          <Link
            href={`/jobs?dataset=${encodeURIComponent(datasetName)}`}
            className="text-sm font-medium text-accent hover:underline"
          >
            Browse all jobs
          </Link>
        }
      >
        {topJobs.length === 0 ? (
          <EmptyState
            title="No positive job matches"
            description="None of the filtered postings overlap with your current skills. Try broadening the search or adding more skills."
            action={
              <Link href={analyzeHref}>
                <Button variant="secondary">Adjust the analysis</Button>
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {topJobs.map((job) => (
              <JobMatchCard key={`${job.title}-${job.company}`} job={job} />
            ))}
          </div>
        )}
      </Section>

      {response.resume_analysis ? (
        <Section
          title="Resume analysis"
          description={response.resume_analysis.privacy_note}
        >
          <div className="rounded-xl border border-border bg-surface p-5">
            <p className="text-sm text-text">
              {response.resume_analysis.explanation}
            </p>
            {response.resume_analysis.resume_skills.length > 0 ? (
              <ul className="mt-4 flex flex-wrap gap-1.5">
                {response.resume_analysis.resume_skills.slice(0, 18).map((skill) => (
                  <li key={skill}>
                    <Badge tone="accent">{formatSkill(skill)}</Badge>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </Section>
      ) : null}
    </div>
  );
}
