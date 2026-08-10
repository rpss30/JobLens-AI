"use client";

import Link from "next/link";

import { JobMatchCard } from "@/components/domain/JobMatchCard";
import { LandingIntro } from "@/components/domain/LandingIntro";
import { ReportDownloads } from "@/components/domain/ReportDownloads";
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
    return <LandingIntro datasetName={datasetName} summary={summary} />;
  }

  const { response, request } = analysis;
  const visibleJobs = response.top_matching_jobs.slice(0, 6);
  const remainingJobs = response.top_matching_jobs.slice(6);

  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Your best role"
          value={response.best_role}
          hint={`Compared against ${formatCount(response.jobs_analyzed)} jobs`}
        />
        <StatTile
          label="Skill match"
          value={formatPercent(response.weighted_match_score)}
          hint="How much of what this role asks for you already have"
          emphasis
        />
        <StatTile
          label="Biggest gap"
          value={formatSkill(response.top_missing_skill)}
          hint="The most in-demand skill you are missing"
        />
        <StatTile
          label="Skills you have"
          value={formatCount(
            response.resume_analysis?.combined_skills.length ??
              request.current_skills.length,
          )}
          hint={response.resume_analysis ? "Including skills found in your resume" : undefined}
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <SaveAnalysisButton />
        <ReportDownloads />
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-2">
        <RoleFitPanel roleScores={response.role_scores} />
        <SkillGapPanel skills={response.recommended_skills} />
      </div>

      <Section
        title="Jobs worth applying to first"
        description="These openings ask for the most skills you already have."
        action={
          <Link
            href={`/jobs?dataset=${encodeURIComponent(datasetName)}`}
            className="text-sm font-medium text-accent hover:underline"
          >
            Browse all postings
          </Link>
        }
      >
        {visibleJobs.length === 0 ? (
          <EmptyState
            title="No close matches yet"
            description="None of these jobs overlap with the skills you listed. Try adding more skills, or widening your search."
            action={
              <Link href={analyzeHref}>
                <Button variant="secondary">Change my search</Button>
              </Link>
            }
          />
        ) : (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visibleJobs.map((job) => (
                <JobMatchCard key={`${job.title}-${job.company}`} job={job} />
              ))}
            </div>

            {remainingJobs.length > 0 ? (
              <details className="group">
                <summary className="inline-flex cursor-pointer list-none items-center rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm font-medium text-text transition-colors hover:bg-surface-muted">
                  Show more matches ({remainingJobs.length})
                </summary>
                <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {remainingJobs.map((job) => (
                    <JobMatchCard key={`${job.title}-${job.company}`} job={job} />
                  ))}
                </div>
              </details>
            ) : null}
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
