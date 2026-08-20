import { Suspense } from "react";

import { SkillBubbleChart } from "@/components/charts/SkillBubbleChart";
import {
  TotalPostingsBadge,
  TotalPostingsBadgeSkeleton,
} from "@/components/domain/TotalPostingsBadge";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { CardSkeleton } from "@/components/ui/States";
import { getMarketInsights } from "@/lib/api/endpoints";
import { resolveDataset, withDataset } from "@/lib/datasets";
import { formatCount, formatSkill } from "@/lib/format";

/** How many rows are shown before the full ranking is revealed. */
const VISIBLE_RANK_COUNT = 12;

function LightbulbIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M7 14.5h4M7.5 16.5h3" />
      <path d="M9 1.75a4.75 4.75 0 0 0-2.75 8.62c.4.3.65.75.7 1.25l.05.38h4l.05-.38c.05-.5.3-.95.7-1.25A4.75 4.75 0 0 0 9 1.75Z" />
    </svg>
  );
}

function RankRow({
  rank,
  label,
  value,
  share,
}: {
  rank: number;
  label: string;
  value: number;
  share: number;
}) {
  return (
    <li className="flex items-center gap-2 py-2 sm:gap-3">
      <span className="w-5 shrink-0 text-xs tabular-nums text-text-subtle">
        {rank}
      </span>
      {/* Takes the spare room on a narrow screen, where the bar is hidden. */}
      <span
        className="min-w-0 flex-1 truncate text-sm text-text"
        title={label}
      >
        {label}
      </span>
      {/* The counts beside it already carry the comparison, so the bar is the
          first thing to go when there is no room for it. */}
      <span className="hidden h-2 min-w-0 rounded-full bg-surface-muted sm:block sm:flex-1">
        <span
          className="block h-2 rounded-full bg-chart-2"
          style={{ width: `${Math.max(share * 100, 2)}%` }}
        />
      </span>
      <span className="w-10 shrink-0 text-right text-sm tabular-nums text-text">
        {formatCount(value)}
      </span>
      <span className="w-10 shrink-0 text-right text-sm tabular-nums text-accent">
        {Math.round(share * 100)}%
      </span>
    </li>
  );
}

async function SkillsDemand({ datasetName }: { datasetName: string }) {
  // 25 is the API's ceiling for this call, and enough to rank meaningfully.
  const insights = await getMarketInsights({ datasetName, topN: 25 });

  const ranked = insights.skill_demand.map((item) => ({
    label: formatSkill(item.skill),
    value: item.job_count,
    // Postings can ask for several skills, so this is the share of postings
    // mentioning the skill, not a slice of a whole.
    share: insights.jobs_analyzed > 0 ? item.job_count / insights.jobs_analyzed : 0,
  }));

  const visible = ranked.slice(0, VISIBLE_RANK_COUNT);
  const remaining = ranked.slice(VISIBLE_RANK_COUNT);
  const leader = ranked[0];

  return (
    <Card>
      <CardBody className="min-w-0 space-y-5 p-5 sm:p-6">
        {leader ? (
          <div className="flex items-start gap-2.5 rounded-xl border border-border bg-surface-muted px-4 py-3 text-sm text-text-muted">
            <span className="mt-0.5 text-accent">
              <LightbulbIcon />
            </span>
            <p>
              <strong className="font-medium text-text">
                {leader.label} is the most in-demand skill
              </strong>
              , appearing in {Math.round(leader.share * 100)}% of all job
              postings in this snapshot.
            </p>
          </div>
        ) : null}
        
        <div className="grid min-w-0 items-start gap-5 lg:grid-cols-2">
          <section className="order-2 min-w-0 w-full rounded-xl border border-border p-4 lg:order-1">
            <h2 className="text-base font-medium text-text">
              Skills ranked by number of postings
            </h2>

            <div className="mt-3 flex items-center gap-2 border-b border-border pb-2 text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle sm:gap-3 sm:text-xs">
              <span className="w-5 shrink-0">#</span>
              <span className="min-w-0 flex-1">Skill</span>
              <span className="hidden min-w-0 sm:block sm:flex-1" />
              <span className="w-10 shrink-0 text-right">Jobs</span>
              <span className="w-10 shrink-0 text-right">Share</span>
            </div>

            <ul className="divide-y divide-border">
              {visible.map((item, index) => (
                <RankRow key={item.label} rank={index + 1} {...item} />
              ))}
            </ul>

            {remaining.length > 0 ? (
              <details className="mt-3">
                <summary className="inline-flex cursor-pointer list-none items-center rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-accent transition-colors hover:bg-surface-muted">
                  View full skill ranking ({remaining.length} more)
                </summary>
                <ul className="mt-2 divide-y divide-border">
                  {remaining.map((item, index) => (
                    <RankRow
                      key={item.label}
                      rank={VISIBLE_RANK_COUNT + index + 1}
                      {...item}
                    />
                  ))}
                </ul>
              </details>
            ) : null}
          </section>

          <section className="order-1 min-w-0 w-full rounded-xl border border-border p-4 lg:order-2">
            <h2 className="text-base font-medium text-text">
              Skills at a glance
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              Circle size represents number of postings.
            </p>
            <div className="mt-3">
              <SkillBubbleChart
                data={visible}
                valueLabel="postings"
                // The skill goes into the search box, and the filters open on
                // arrival so it is clear what narrowed the list.
                hrefFor={(skill) =>
                  withDataset(
                    `/jobs?q=${encodeURIComponent(skill)}&filters=open`,
                    datasetName,
                  )
                }
              />
            </div>
          </section>
        </div>
      </CardBody>
    </Card>
  );
}

export default async function SkillsDemandPage({
  searchParams,
}: PageProps<"/skills">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Skills Demand"
        description="How many postings in this snapshot ask for each skill."
        action={
          <Suspense fallback={<TotalPostingsBadgeSkeleton />}>
            <TotalPostingsBadge datasetName={datasetName} />
          </Suspense>
        }
      />

      <Suspense key={datasetName} fallback={<CardSkeleton rows={10} />}>
        <SkillsDemand datasetName={datasetName} />
      </Suspense>
    </>
  );
}
