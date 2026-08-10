import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import type { DatasetSnapshotSummary } from "@/lib/api/types";
import { formatCount } from "@/lib/format";

const STEPS = [
  {
    title: "1. Tell us what you can do",
    body: "List the skills you already have, or paste your resume and let JobLens pull them out for you. Nothing you paste is saved.",
  },
  {
    title: "2. We read real job ads",
    body: "JobLens goes through real job postings from company career pages and works out which skills each one is actually asking for.",
  },
  {
    title: "3. You see where you stand",
    body: "Get the roles you fit best, the skills holding you back, and the specific jobs worth applying to first.",
  },
];

export function LandingIntro({
  datasetName,
  summary,
}: {
  datasetName: string;
  summary: DatasetSnapshotSummary;
}) {
  return (
    <div className="space-y-8">
      <Card>
        <CardBody className="px-6 py-8 sm:px-10 sm:py-12">
          <p className="text-sm font-medium text-text-muted">
            Job market intelligence
          </p>
          <h2 className="mt-3 max-w-2xl text-2xl font-semibold tracking-tight text-text sm:text-3xl">
            Find out which jobs you are ready for, and exactly what is standing
            in the way.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-text-muted sm:text-base">
            JobLens compares your skills against{" "}
            {formatCount(summary.job_count)} real job openings from{" "}
            {formatCount(summary.company_count)} companies. Instead of guessing
            what employers want, you get a clear picture of how you match, what
            you are missing, and which openings to go after first.
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-3">
            <Link href={`/analyze?dataset=${encodeURIComponent(datasetName)}`}>
              <Button>Check my skills</Button>
            </Link>
            <Link href={`/jobs?dataset=${encodeURIComponent(datasetName)}`}>
              <Button variant="secondary">Just browse the jobs</Button>
            </Link>
          </div>
        </CardBody>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        {STEPS.map((step) => (
          <div
            key={step.title}
            className="rounded-xl border border-border bg-surface p-5"
          >
            <h3 className="text-sm font-semibold text-text">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-text-muted">
              {step.body}
            </p>
          </div>
        ))}
      </div>

      <Card>
        <CardBody className="px-6 py-6">
          <h3 className="text-sm font-semibold text-text">
            What you can do here
          </h3>
          <dl className="mt-4 grid gap-x-8 gap-y-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-text">Analyze</dt>
              <dd className="mt-1 text-sm text-text-muted">
                See how your skills score against real openings.
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text">Jobs</dt>
              <dd className="mt-1 text-sm text-text-muted">
                Search and filter every opening, and open the original posting.
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text">Skills &amp; Market</dt>
              <dd className="mt-1 text-sm text-text-muted">
                Find out which skills employers are asking for most.
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-text">History</dt>
              <dd className="mt-1 text-sm text-text-muted">
                Save a result and come back to it as your skills grow.
              </dd>
            </div>
          </dl>
        </CardBody>
      </Card>
    </div>
  );
}
