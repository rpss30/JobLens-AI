import Link from "next/link";
import { Suspense } from "react";

import { CompanyLogo } from "@/components/domain/CompanyLogo";
import {
  TotalPostingsBadge,
  TotalPostingsBadgeSkeleton,
} from "@/components/domain/TotalPostingsBadge";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { DataTable } from "@/components/ui/DataTable";
import { CardSkeleton } from "@/components/ui/States";
import { TableDisclosure } from "@/components/ui/TableDisclosure";
import { getMarketInsights } from "@/lib/api/endpoints";
import type { CompanyDemand } from "@/lib/api/types";
import { resolveDataset, withDataset } from "@/lib/datasets";
import { formatCount, formatSkill } from "@/lib/format";

/** How many employers get a card before the rest become a single line. */
const CARD_COUNT = 8;

function BuildingIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M3.25 17.25h13.5M4.75 17.25V4.25a1 1 0 0 1 1-1h5.5a1 1 0 0 1 1 1v13M12.25 8.25h2a1 1 0 0 1 1 1v8" />
      <path d="M7.25 6.75h2M7.25 9.75h2M7.25 12.75h2" />
    </svg>
  );
}

function PinIcon() {
  return (
    <svg
      width="13"
      height="13"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M16 8.5c0 4-6 9-6 9s-6-5-6-9a6 6 0 0 1 12 0Z" />
      <circle cx="10" cy="8.25" r="2" />
    </svg>
  );
}

function WorkplaceIcon({ workplace }: { workplace: string }) {
  const shared = {
    width: 13,
    height: 13,
    viewBox: "0 0 20 20",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    className: "shrink-0",
  };

  if (workplace === "Remote") {
    return (
      <svg {...shared}>
        <path d="M2.75 7.5a10.5 10.5 0 0 1 14.5 0M5.5 10.5a6.5 6.5 0 0 1 9 0" />
        <circle cx="10" cy="14.5" r="1.25" />
      </svg>
    );
  }

  if (workplace === "Hybrid") {
    return (
      <svg {...shared}>
        <path d="M3.25 9.25 10 3.75l6.75 5.5" />
        <path d="M5.25 10.75v5.5h9.5v-5.5" />
      </svg>
    );
  }

  return (
    <svg {...shared}>
      <path d="M4.75 16.75V4.5a.75.75 0 0 1 .75-.75h6.5a.75.75 0 0 1 .75.75v12.25M12.75 9.25h2.5v7.5M3.5 16.75h13" />
    </svg>
  );
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2 py-1 text-xs text-text-muted">
      {children}
    </span>
  );
}

/**
 * Where an employer's postings live on the Jobs page.
 *
 * The employer is named rather than searched for: several here share a name
 * with a tool other postings ask for, and searching "MongoDB" or "Stripe"
 * returns their competitors' jobs alongside their own. The Jobs filters show
 * categories rather than employers now, so this one rides along hidden.
 */
function jobsHref(company: string, datasetName: string): string {
  return withDataset(
    `/jobs?company=${encodeURIComponent(company)}&filters=open`,
    datasetName,
  );
}

function CompanyCard({
  company,
  datasetName,
}: {
  company: CompanyDemand;
  datasetName: string;
}) {
  return (
    // min-w-0 or the grid track refuses to shrink below the widest skill
    // line, and the card runs past the viewport with its count clipped off.
    <article className="flex min-w-0 flex-col rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center gap-3">
        <CompanyLogo name={company.company} domain={company.domain} />
        <h3
          className="min-w-0 flex-1 truncate text-base font-medium text-text"
          title={company.company}
        >
          {company.company}
        </h3>
        <span className="shrink-0 rounded-lg bg-accent-soft px-2 py-1 text-xs font-medium tabular-nums text-accent">
          {formatCount(company.job_count)}{" "}
          {company.job_count === 1 ? "job" : "jobs"}
        </span>
      </div>

      {company.role_categories.length > 0 ? (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {company.role_categories.map((category) => (
            <li
              key={category}
              className="rounded-md bg-surface-muted px-2 py-0.5 text-xs text-text-muted"
            >
              {category}
            </li>
          ))}
        </ul>
      ) : null}

      {company.top_skills.length > 0 ? (
        <>
          <p className="mt-3 text-[0.6875rem] font-medium uppercase tracking-wide text-text-subtle">
            Top skills
          </p>
          <p className="mt-1 truncate text-sm text-text" title={company.top_skills.map(formatSkill).join(" · ")}>
            {company.top_skills.map(formatSkill).join(" · ")}
          </p>
        </>
      ) : null}

      {company.location || company.workplace_type ? (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-border pt-3">
          {company.location ? (
            <Pill>
              <PinIcon />
              <span className="truncate">{company.location}</span>
            </Pill>
          ) : null}
          {company.workplace_type ? (
            <Pill>
              <WorkplaceIcon workplace={company.workplace_type} />
              {company.workplace_type}
            </Pill>
          ) : null}
        </div>
      ) : null}

      <Link
        href={jobsHref(company.company, datasetName)}
        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-accent transition-colors hover:text-text"
      >
        View jobs
        <span aria-hidden="true">→</span>
      </Link>
    </article>
  );
}

async function TopCompanies({ datasetName }: { datasetName: string }) {
  // 25 is the API's ceiling, and more employers than the cards will show.
  const insights = await getMarketInsights({ datasetName, topN: 25 });
  const companies = insights.top_companies;

  if (companies.length === 0) {
    return (
      <Card>
        <CardBody className="p-5">
          <p className="text-sm text-text-muted">
            No employers were recorded for this dataset.
          </p>
        </CardBody>
      </Card>
    );
  }

  const carded = companies.slice(0, CARD_COUNT);
  const remaining = companies.slice(CARD_COUNT);

  return (
    <Card>
      <CardBody className="space-y-5 p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <span className="inline-flex rounded-xl bg-accent-soft p-2.5 text-accent">
            <BuildingIcon />
          </span>
          <div className="min-w-0">
            <h2 className="text-lg font-medium text-text">
              Companies hiring now
            </h2>
            <p className="text-sm text-text-muted">
              Employers with the most open roles
            </p>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {carded.map((company) => (
            <CompanyCard
              key={company.company}
              company={company}
              datasetName={datasetName}
            />
          ))}
        </div>

        {remaining.length > 0 ? (
          <section className="border-t border-border pt-4">
            <h3 className="text-sm font-medium text-text">
              More companies hiring
            </h3>
            <ul className="mt-3 flex flex-wrap gap-2">
              {remaining.map((company) => (
                <li key={company.company}>
                  <Link
                    href={jobsHref(company.company, datasetName)}
                    className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm transition-colors hover:bg-surface-muted"
                  >
                    <CompanyLogo
                      name={company.company}
                      domain={company.domain}
                    />
                    <span className="truncate text-text">
                      {company.company}
                    </span>
                    <span className="tabular-nums text-text-muted">
                      {formatCount(company.job_count)}{" "}
                      {company.job_count === 1 ? "job" : "jobs"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </CardBody>

      <TableDisclosure label={`View all ${companies.length} companies`}>
        <DataTable
          columns={[
            {
              key: "company",
              header: "Company",
              render: (row: CompanyDemand) => (
                <span className="inline-flex items-center gap-2">
                  <CompanyLogo
                    name={row.company}
                    domain={row.domain}
                    size="sm"
                  />
                  {row.company}
                </span>
              ),
            },
            {
              key: "roles",
              header: "Roles",
              render: (row: CompanyDemand) => row.role_categories.join(", "),
            },
            {
              key: "location",
              header: "Location",
              render: (row: CompanyDemand) => row.location,
            },
            {
              key: "workplace",
              header: "Workplace",
              render: (row: CompanyDemand) => row.workplace_type,
            },
            {
              key: "job_count",
              header: "Postings",
              align: "right",
              render: (row: CompanyDemand) => formatCount(row.job_count),
            },
          ]}
          rows={companies}
          getRowKey={(row) => row.company}
          caption="Postings by company"
        />
      </TableDisclosure>
    </Card>
  );
}

export default async function TopCompaniesPage({
  searchParams,
}: PageProps<"/skills/companies">) {
  const params = await searchParams;
  const datasetName = resolveDataset(params.dataset);

  return (
    <>
      <PageHeader
        title="Top Hiring Companies"
        description="Employers with the most postings in this snapshot."
        action={
          <Suspense fallback={<TotalPostingsBadgeSkeleton />}>
            <TotalPostingsBadge datasetName={datasetName} />
          </Suspense>
        }
      />

      <Suspense key={datasetName} fallback={<CardSkeleton rows={10} />}>
        <TopCompanies datasetName={datasetName} />
      </Suspense>
    </>
  );
}
