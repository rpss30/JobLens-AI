"use client";

import { ReportDownloads } from "@/components/domain/ReportDownloads";
import { SaveAnalysisButton } from "@/components/domain/SaveAnalysisButton";
import { Button } from "@/components/ui/Button";

/** A pencil over a page: starting again is writing a new one. */
function NewAnalysisIcon() {
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M9 4.25H5.25a1.5 1.5 0 0 0-1.5 1.5v9a1.5 1.5 0 0 0 1.5 1.5h9a1.5 1.5 0 0 0 1.5-1.5V11" />
      <path d="M13.4 3.6a1.6 1.6 0 0 1 2.26 2.26l-5.5 5.5-2.9.64.64-2.9Z" />
    </svg>
  );
}
import { useAnalysis } from "@/context/AnalysisContext";

/**
 * What can be done with a result, beside the heading that names it.
 *
 * Starting again is the filled one: a reader who has finished with a result
 * is far likelier to want another than to want the file.
 */
export function ResultsActions() {
  const { analysis, clearAnalysis } = useAnalysis();

  if (!analysis) {
    return null;
  }

  return (
    /* Nowrap: the three sit on one line at every width, because on a phone
       two of them are down to their icon. */
    <div className="flex flex-nowrap items-center gap-2 sm:gap-3">
      {/* Puts the form back where the result is, rather than sending the
          reader off to find it. */}
      {/* The one that keeps its label everywhere: it is the way out of a
          result, and an icon alone would not say so. */}
      <Button onClick={clearAnalysis}>
        Run New Analysis
        <NewAnalysisIcon />
      </Button>
      <SaveAnalysisButton />
      <ReportDownloads />
    </div>
  );
}
