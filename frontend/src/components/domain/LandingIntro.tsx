import Link from "next/link";

import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import type { DatasetSnapshotSummary } from "@/lib/api/types";

interface Step {
  title: string;
  intro?: string;
  bullets?: string[];
  body: string;
}

const STEPS: Step[] = [
  {
    title: "Step 1 - What skills you have?",
    intro: "Go to the ‘Analyze’ tab and enter:",
    bullets: [
      "A list of skills you have,",
      "Choose one of the preset profiles, or",
      "Directly paste your resume",
    ],
    body: "And enter how much experience you have.",
  },
  {
    title: "Step 2 - What are you seeking?",
    intro: "Enter the role you’re looking for by either:",
    bullets: ["Typing keywords, or", "Selecting a job title from the list"],
    body: "Then enter the location and experience level for your search.",
  },
  {
    title: "Step 3 - Your personalized results",
    body: "You get to see the top matches based on your profile and search filters, along with skill gaps and assessment for each matched job with direct links to their posting. You can also download a PDF or markdown of the report.",
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

  return (
    <div className="space-y-8">
      <Card>
        <CardBody className="p-6">
          <p className="text-xs text-text-muted">Job market intelligence</p>
          <h2 className="mt-2 text-xl font-medium tracking-tight text-text">
            What does JobLens do?
          </h2>
          <p className="mt-3 text-[0.9375rem] leading-relaxed text-text-muted">
            JobLens compares the skills you have against what real job postings
            are actually asking for, then shows you which roles you fit best and
            which specific skills are holding you back. It reads full job
            descriptions rather than matching on job titles.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link href={`/analyze?dataset=${encodedDataset}`}>
              <Button size="lg">Get Started</Button>
            </Link>
            <Link href={`/jobs?dataset=${encodedDataset}`}>
              <Button variant="secondary" size="lg">
                Browse Jobs
              </Button>
            </Link>
          </div>
        </CardBody>
      </Card>

      {/* The three cards share a bottom edge in the design, so they stretch
          to the tallest rather than sitting at their natural heights. */}
      <div className="grid gap-6 md:grid-cols-3">
        {STEPS.map((step) => (
          <Card key={step.title}>
            <CardBody className="p-6">
              <h3 className="text-xl font-medium tracking-tight text-text">
                {step.title}
              </h3>
              {step.intro ? (
                <p className="mt-3 text-[0.9375rem] leading-relaxed text-text-muted">
                  {step.intro}
                </p>
              ) : null}
              {step.bullets ? (
                <ul className="mt-1.5 list-disc space-y-1 pl-5 text-[0.9375rem] leading-relaxed text-text-muted">
                  {step.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              ) : null}
              <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-text-muted">
                {step.body}
              </p>
            </CardBody>
          </Card>
        ))}
      </div>

      <Card>
        <CardBody className="space-y-5 p-6">
          <h2 className="text-xl font-medium tracking-tight text-text">
            Where are the job postings from?
          </h2>
          <p className="text-[0.9375rem] leading-relaxed text-text-muted">
            Directly from companies&rsquo; own career pages and the Greenhouse,
            Lever, and Ashby job boards those employers publish. These are real
            postings, not sample data or aggregator listings, and every match
            links back to the original posting.
          </p>
          {summary.refreshed_date ? (
            <p className="text-[0.9375rem] leading-relaxed text-text-muted">
              Last updated: {summary.refreshed_date}
            </p>
          ) : null}
          <p className="text-[0.9375rem] leading-relaxed text-text-muted">
            You can also upload your own dataset that is a spreadsheet (CSV)
            with a column for title, company, location, description, and
            experience level.
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
