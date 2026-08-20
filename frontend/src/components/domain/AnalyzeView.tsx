"use client";

import { useEffect, useRef } from "react";

import { AnalysisResults } from "@/components/domain/AnalysisResults";
import { AnalyzeForm } from "@/components/domain/AnalyzeForm";
import { PageHeader } from "@/components/layout/PageHeader";
import { useAnalysis } from "@/context/AnalysisContext";
import type { FilterOptions } from "@/lib/api/types";

export const ANALYZE_HEADING = {
  title: "Analyze",
  description:
    "Tell us what you can do, and we will show you which jobs you fit and what you are missing.",
};

const RESULTS_HEADING = {
  title: "Results",
  description:
    "Where you fit, which skills are holding you back, and the postings worth applying to first.",
};

/**
 * The form, or the result it produced, under the heading that describes it.
 *
 * A result is read where it was asked for rather than on Overview, which is
 * the landing page. Whether one exists is only known on the client, so both
 * the choice and the heading above it are made here.
 */
export function AnalyzeView({
  filterOptions,
  datasetName,
}: {
  filterOptions: FilterOptions;
  datasetName: string;
}) {
  const { analysis } = useAnalysis();
  const hadAnalysis = useRef(analysis !== null);

  useEffect(() => {
    const hasAnalysis = analysis !== null;

    // The submit sits at the foot of a long form, so a result arriving in its
    // place would otherwise open halfway down itself. Only on the change:
    // scrolling on every render would fight the reader.
    if (hasAnalysis && !hadAnalysis.current) {
      window.scrollTo({ top: 0 });
    }

    hadAnalysis.current = hasAnalysis;
  }, [analysis]);

  const heading = analysis ? RESULTS_HEADING : ANALYZE_HEADING;

  return (
    <>
      <PageHeader title={heading.title} description={heading.description} />

      {analysis ? (
        <AnalysisResults datasetName={datasetName} />
      ) : (
        <AnalyzeForm filterOptions={filterOptions} datasetName={datasetName} />
      )}
    </>
  );
}
