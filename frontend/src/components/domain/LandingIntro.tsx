import Link from "next/link";
import { Fragment, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { CountUp } from "@/components/ui/CountUp";
import type { DatasetSnapshotSummary } from "@/lib/api/types";
import { formatCount, formatDate } from "@/lib/format";

/** The small accent label that names each band of the page. */
function Eyebrow({ children }: { children: string }) {
  return (
    <p className="text-xs font-bold uppercase tracking-wider text-accent">
      {children}
    </p>
  );
}

/**
 * The tinted circle every icon on this page sits in.
 *
 * accent-soft rather than a literal tint, so the inside of the ring follows
 * the theme instead of staying pale on a dark background.
 */
function IconRing({
  children,
  size = "md",
}: {
  children: ReactNode;
  size?: "sm" | "md";
}) {
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full border-2 border-accent bg-accent-soft text-accent ${
        size === "sm" ? "size-11" : "size-16"
      }`}
    >
      {children}
    </span>
  );
}

function CheckIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m8 12.5 2.75 2.75L16 9.5" />
    </svg>
  );
}

function TargetIcon({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="7.5" />
      <circle cx="12" cy="12" r="3.5" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" />
    </svg>
  );
}

function TrendIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m5 15.5 4.5-4.5 3 3L19 7.5" />
      <path d="M15 7.5h4v4" />
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="8.5" r="3.4" />
      <path d="M5.5 19.5c0-3.4 2.9-5.2 6.5-5.2s6.5 1.8 6.5 5.2" />
    </svg>
  );
}

function CompassIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="8.2" />
      <path d="m15.6 8.4-2.1 5.1-5.1 2.1 2.1-5.1z" />
    </svg>
  );
}

function BarsIcon({ size = 30 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 18.5v-5M12 18.5V7M18 18.5v-8" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg
      width="26"
      height="16"
      viewBox="0 0 30 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M2 8h24M21 3l5 5-5 5" strokeDasharray="3 3" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3.5 5.5 6v5.5c0 4 2.7 7.3 6.5 9 3.8-1.7 6.5-5 6.5-9V6z" />
    </svg>
  );
}

function DocumentIcon({ size = 26 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M14 3.5H7.5A1.5 1.5 0 0 0 6 5v14a1.5 1.5 0 0 0 1.5 1.5h9A1.5 1.5 0 0 0 18 19V7.5z" />
      <path d="M14 3.5V7a.5.5 0 0 0 .5.5H18M9 12h6M9 15.5h4" />
    </svg>
  );
}

function CalendarIcon({ size = 26 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="4" y="5.5" width="16" height="14.5" rx="2" />
      <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
    </svg>
  );
}

/**
 * A window standing in for the results the page is selling.
 *
 * Drawn rather than photographed: a committed screenshot of this product has
 * already gone stale once, and shapes carry the idea without claiming to be
 * numbers anybody produced.
 */
function HeroPreview() {
  return (
    <div
      aria-hidden="true"
      className="overflow-hidden rounded-2xl border border-border bg-surface shadow-[0_18px_50px_rgba(16,21,31,0.10)]"
    >
      <div className="flex items-center gap-1.5 border-b border-border bg-surface-muted px-4 py-3">
        <span className="size-2.5 rounded-full bg-border-strong" />
        <span className="size-2.5 rounded-full bg-border-strong" />
        <span className="size-2.5 rounded-full bg-border-strong" />
      </div>

      <div className="space-y-4 p-5">
        <div className="flex items-center justify-between">
          <span className="h-3 w-24 rounded-full bg-text/15" />
          <div className="flex gap-1.5">
            <span className="h-5 w-16 rounded-md bg-accent-fill" />
            <span className="h-5 w-14 rounded-md bg-surface-muted" />
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2">
          {[0, 1, 2, 3].map((tile) => (
            <div
              key={tile}
              className="space-y-1.5 rounded-lg border border-border p-2.5"
            >
              <span className="block h-1.5 w-8 rounded-full bg-text/10" />
              <span className="block h-3 w-12 rounded-full bg-text/25" />
              <span className="block h-1.5 w-full rounded-full bg-text/10" />
            </div>
          ))}
        </div>

        <div className="grid grid-cols-[1.2fr_1fr] gap-3">
          <div className="flex h-40 items-center justify-center rounded-lg border border-border">
            {/* The radar the role fit panel draws, reduced to its outline. */}
            <svg
              viewBox="0 0 120 120"
              className="h-32 w-32 text-accent"
              fill="none"
              stroke="currentColor"
            >
              <polygon
                points="60,14 100,37 100,83 60,106 20,83 20,37"
                strokeWidth="1"
                className="opacity-30"
              />
              <polygon
                points="60,37 80,48 80,72 60,83 40,72 40,48"
                strokeWidth="1"
                className="opacity-30"
              />
              <polygon
                points="60,26 92,44 84,78 58,92 30,74 34,46"
                strokeWidth="1.5"
                fill="currentColor"
                fillOpacity="0.16"
              />
            </svg>
          </div>

          <div className="space-y-2 rounded-lg border border-border p-3">
            <span className="block h-2 w-20 rounded-full bg-text/15" />
            {[16, 13, 15, 11, 14, 9].map((width, index) => (
              <div key={index} className="flex items-center gap-2">
                <span
                  className="h-1.5 rounded-full bg-accent/45"
                  style={{ width: `${width * 4}px` }}
                />
                <span className="h-1.5 flex-1 rounded-full bg-text/8" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const HIGHLIGHTS = [
  {
    icon: <CheckIcon />,
    title: "Real job postings",
    body: "From employer sources",
  },
  {
    icon: <TargetIcon />,
    title: "Skill-level matching",
    body: "Reads full job descriptions",
  },
  {
    icon: <TrendIcon />,
    title: "Personalized gaps",
    body: "Focus on what matters",
  },
];

const STEPS = [
  {
    number: "01",
    icon: <PersonIcon />,
    title: "Build your profile",
    body: "Add your skills or paste your resume. JobLens builds your skill profile",
  },
  {
    number: "02",
    icon: <CompassIcon />,
    title: "Define what matters",
    body: "Choose your preferred location and current experience level for your search",
  },
  {
    number: "03",
    icon: <BarsIcon />,
    title: "See where you stand",
    body: "Explore role fit, skill gaps, and matching jobs with direct links to postings",
  },
];

export function LandingIntro({
  datasetName,
  summary,
}: {
  datasetName: string;
  summary: DatasetSnapshotSummary;
}) {
  const encodedDataset = encodeURIComponent(datasetName);

  const facts = [
    {
      icon: <DocumentIcon size={34} />,
      count: summary.job_count,
      value: formatCount(summary.job_count),
      label: "Job postings in\nthe current snapshot",
    },
    {
      icon: <BarsIcon size={34} />,
      count: summary.company_count,
      value: formatCount(summary.company_count),
      label: "Companies across\nthe dataset",
    },
    {
      icon: <CalendarIcon size={34} />,
      // The snapshot spells the month out in full, which wraps the tile.
      // formatDate shortens it and hands back the original if it cannot.
      value: formatDate(summary.refreshed_date) || "Not recorded",
      label: "Last updated\nData refreshed weekly",
    },
  ];

  return (
    <div className="space-y-10">
      <section className="rise-in grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div>
          <Eyebrow>Job market intelligence</Eyebrow>

          <h2 className="mt-3 text-3xl font-semibold leading-tight tracking-tight text-text sm:text-4xl">
            Understand where you fit in the job market
          </h2>

          <p className="mt-4 max-w-xl text-base leading-relaxed text-text-muted">
            Compare your skills against real job postings, discover the roles
            you fit best, and see what skills are holding you back
          </p>

          {/* The two actions stack down one column and the claims down the
              other, so the pair reads as a single block at any width. */}
          {/* Halves on a narrow screen so the pair fills the row, natural
              widths once there is room for them to sit as they are. */}
          <div className="mt-8 grid grid-cols-2 gap-3 lg:flex lg:flex-wrap lg:items-center">
            <Link href={`/analyze?dataset=${encodedDataset}`} className="contents">
              <Button variant="strong" size="md">
                Analyze my fit
                <span aria-hidden="true" className="ml-2">
                  &rarr;
                </span>
              </Button>
            </Link>
            <Link href={`/jobs?dataset=${encodedDataset}`} className="contents">
              <Button variant="secondary" size="md">
                Browse Jobs
              </Button>
            </Link>
          </div>

          {/* Centred under their marks on a narrow screen, ranged left once
              they sit beside the window rather than above it. */}
          <ul className="mt-10 grid grid-cols-3 gap-6">
            {HIGHLIGHTS.map((highlight) => (
              <li
                key={highlight.title}
                className="flex flex-col items-center text-center lg:items-start lg:text-left"
              >
                <IconRing size="sm">{highlight.icon}</IconRing>
                <p className="mt-3 text-sm font-medium text-text">
                  {highlight.title}
                </p>
                <p className="mt-1.5 text-xs text-text-muted">
                  {highlight.body}
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div className="hidden lg:block">
          <HeroPreview />
        </div>
      </section>

      <section className="rise-in" style={{ animationDelay: "260ms" }}>
        <Eyebrow>How it works</Eyebrow>

        {/* Steps and the arrows between them run in source order, so the row
            places itself rather than being pinned column by column. */}
        <ol className="mt-5 grid gap-3 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-stretch md:gap-4">
          {STEPS.map((step, index) => (
            <Fragment key={step.number}>
              {index > 0 ? (
                <li
                  aria-hidden="true"
                  className="hidden self-center text-accent md:block"
                >
                  <ArrowIcon />
                </li>
              ) : null}

              <li className="h-full">
                <Card className="h-full">
                  <CardBody className="flex h-full items-center gap-5 py-5">
                    <IconRing>{step.icon}</IconRing>
                    <div className="min-w-0">
                      <p className="text-2xl font-semibold tracking-tight text-accent">
                        {step.number}
                      </p>
                      <p className="mt-1 text-base font-medium text-text">
                        {step.title}
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-text-muted">
                        {step.body}
                      </p>
                    </div>
                  </CardBody>
                </Card>
              </li>
            </Fragment>
          ))}
        </ol>
      </section>

      <section className="rise-in" style={{ animationDelay: "520ms" }}>
        <Eyebrow>Data behind JobLens</Eyebrow>

        <div className="mt-6 grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] lg:gap-10">
          {/* Given a step card's own box, a 1px edge plus its inset, so this
              icon and its words run down the same line as the steps above at
              every width, not only where the cards sit side by side. */}
          <div className="grid grid-cols-[auto_1fr] items-center gap-x-5 gap-y-3 border-l border-transparent pl-5">
            <h2 className="col-start-2 row-start-1 text-xl font-medium tracking-tight text-text">
              Data you can trust
            </h2>

            <span className="col-start-1 row-start-2 self-center lg:row-span-2 lg:row-start-1">
              <IconRing>
                <ShieldIcon />
              </IconRing>
            </span>

            <div className="col-start-2 row-start-2 min-w-0">
              <p className="text-sm leading-relaxed text-text-muted">
                We pull job postings directly from employer career pages and
                the Greenhouse, Lever, and Ashby job boards those companies
                use.
              </p>
              <p className="mt-3 text-sm leading-relaxed text-text-muted">
                Every match links back to the original posting
              </p>
            </div>
          </div>

          {/* Divided rather than boxed: three readings of one dataset, not
              three separate things. */}
          {/* Three shared rows rather than three independent stacks, so the
              labels line up even where the date takes two lines above them. */}
          <dl className="grid grid-cols-3 grid-rows-[auto_auto_auto] gap-x-4 sm:gap-0 sm:divide-x sm:divide-border">
            {facts.map((fact) => (
              <div
                key={fact.label}
                className="row-span-3 grid grid-rows-subgrid justify-items-center gap-y-3 text-center sm:justify-items-start sm:px-6 sm:text-left sm:first:pl-0 sm:last:pr-0"
              >
                <span className="inline-flex text-accent">{fact.icon}</span>
                <dd
                  // The date runs longer than a count, so it is set smaller
                  // rather than pushing its own column out of step.
                  className={`font-semibold tracking-tight text-text ${
                    typeof fact.count === "number"
                      ? "text-2xl"
                      : "text-xl sm:text-2xl"
                  }`}
                >
                  {typeof fact.count === "number" ? (
                    <CountUp
                      value={fact.count}
                      durationMs={1800}
                      format={formatCount}
                    />
                  ) : (
                    fact.value
                  )}
                </dd>
                <dt className="whitespace-pre-line text-sm leading-relaxed text-text-muted">
                  {fact.label}
                </dt>
              </div>
            ))}
          </dl>
        </div>

        <div className="mt-8 flex justify-center sm:justify-start">
          <Link href={`/datasets?dataset=${encodedDataset}`}>
            <Button variant="secondary" size="md">
              View Datasets
              <span aria-hidden="true" className="ml-2">
                &rarr;
              </span>
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
