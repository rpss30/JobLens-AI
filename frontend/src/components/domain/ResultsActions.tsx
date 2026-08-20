"use client";

import { ReportDownloads } from "@/components/domain/ReportDownloads";
import { SaveAnalysisButton } from "@/components/domain/SaveAnalysisButton";
import { Button } from "@/components/ui/Button";
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
    <div className="flex flex-wrap items-center gap-3">
      {/* Puts the form back where the result is, rather than sending the
          reader off to find it. */}
      <Button onClick={clearAnalysis}>Run New Analysis</Button>
      <SaveAnalysisButton />
      <ReportDownloads />
    </div>
  );
}
