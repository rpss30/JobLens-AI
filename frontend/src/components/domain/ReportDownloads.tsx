"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { useAnalysis } from "@/context/AnalysisContext";
import { useToast } from "@/context/ToastContext";

type ReportFormat = "markdown" | "pdf";

const FORMAT_LABELS: Record<ReportFormat, string> = {
  markdown: "Markdown report",
  pdf: "PDF report",
};

export function ReportDownloads() {
  const { analysis } = useAnalysis();
  const { showToast } = useToast();
  const [pendingFormat, setPendingFormat] = useState<ReportFormat | null>(null);

  if (!analysis) {
    return null;
  }

  async function handleDownload(reportFormat: ReportFormat) {
    if (!analysis) {
      return;
    }

    setPendingFormat(reportFormat);

    try {
      const response = await fetch(
        `/api/reports/candidate?format=${reportFormat}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(analysis.request),
        },
      );

      if (!response.ok) {
        const payload = (await response.json()) as { detail?: string };
        showToast(
          payload.detail ?? "The report could not be created.",
          "error",
        );
        return;
      }

      // Read the filename the API chose rather than hardcoding it here.
      const disposition = response.headers.get("content-disposition") ?? "";
      const filename =
        disposition.match(/filename="([^"]+)"/)?.[1] ??
        `joblens_report.${reportFormat === "pdf" ? "pdf" : "md"}`;

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);

      const downloadLink = document.createElement("a");
      downloadLink.href = objectUrl;
      downloadLink.download = filename;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      downloadLink.remove();
      URL.revokeObjectURL(objectUrl);

      showToast(`Downloaded ${filename}.`);
    } catch {
      showToast("Could not reach JobLens. Check your connection.", "error");
    } finally {
      setPendingFormat(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {(Object.keys(FORMAT_LABELS) as ReportFormat[]).map((reportFormat) => (
        <Button
          key={reportFormat}
          variant="secondary"
          size="sm"
          onClick={() => handleDownload(reportFormat)}
          disabled={pendingFormat !== null}
        >
          {pendingFormat === reportFormat
            ? "Preparing…"
            : `Download ${FORMAT_LABELS[reportFormat]}`}
        </Button>
      ))}
    </div>
  );
}
