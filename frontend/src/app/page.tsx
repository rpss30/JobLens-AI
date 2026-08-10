import Link from "next/link";
import { Suspense } from "react";

import { OverviewContent } from "@/components/domain/OverviewContent";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/Button";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { CardSkeleton, Skeleton } from "@/components/ui/States";
import { getFilterOptions } from "@/lib/api/endpoints";
import { resolveDataset } from "@/lib/datasets";
import { formatCount, formatDatasetLabel } from "@/lib/format";

async function OverviewSection({ datasetName }: { datasetName: string }) {
  const filterOptions = await getFilterOptions(datasetName);
  const { summary } = filterOptions;
  const isCanadaSnapshot = filterOptions.dataset_name === "canada_snapshot";

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <InfoTooltip label={formatDatasetLabel(filterOptions.dataset_name)}>
          {isCanadaSnapshot ? (
            <>
              <strong className="text-text">Where these jobs come from</strong>
              <br />
              {formatCount(summary.job_count)} openings collected directly from
              the career pages of {formatCount(summary.company_count)} Canadian
              employers, across {formatCount(summary.location_count)} locations.
              {summary.refreshed_date ? (
                <> Last updated {summary.refreshed_date}.</>
              ) : null}
              <br />
              <br />
              These are real postings, not made-up examples. JobLens reads each
              description to work out which skills it asks for.
            </>
          ) : (
            <>
              <strong className="text-text">About this dataset</strong>
              <br />
              {formatCount(summary.job_count)} job openings from{" "}
              {formatCount(summary.company_count)} companies across{" "}
              {formatCount(summary.location_count)} locations. Switch datasets
              from the menu at the top of the page.
            </>
          )}
        </InfoTooltip>
      </div>

      <OverviewContent datasetName={datasetName} summary={summary} />
    </>
  );
}

export default async function OverviewPage({ searchParams }: PageProps<"/">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Overview"
        description="Your results at a glance, based on real job openings."
        action={
          <Link href={`/analyze?dataset=${encodeURIComponent(datasetName)}`}>
            <Button>Check my skills</Button>
          </Link>
        }
      />

      <Suspense
        key={datasetName}
        fallback={
          <>
            <Skeleton className="h-6 w-40" />
            <CardSkeleton rows={6} />
          </>
        }
      >
        <OverviewSection datasetName={datasetName} />
      </Suspense>
    </>
  );
}
