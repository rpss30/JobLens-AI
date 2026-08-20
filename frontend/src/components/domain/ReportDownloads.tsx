"use client";

import { useEffect, useRef, useState } from "react";

import { useAnalysis } from "@/context/AnalysisContext";
import { useToast } from "@/context/ToastContext";

type ReportFormat = "markdown" | "pdf";

const FORMAT_LABELS: Record<ReportFormat, string> = {
  markdown: "Markdown",
  pdf: "PDF",
};

function ChevronIcon({ isOpen }: { isOpen: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={`text-text-muted transition-transform ${
        isOpen ? "rotate-180" : ""
      }`}
    >
      <path d="m5.5 7.75 4.5 4.5 4.5-4.5" />
    </svg>
  );
}

/**
 * The report, in whichever format the reader wants it.
 *
 * One control rather than a button per format: the choice of file type is not
 * two separate actions, and spelling both out put two near-identical buttons
 * beside each other in the page's busiest row.
 */
export function ReportDownloads() {
  const { analysis } = useAnalysis();
  const { showToast } = useToast();
  const [pendingFormat, setPendingFormat] = useState<ReportFormat | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDetailsElement | null>(null);

  /*
   * A details element only closes from its own summary, so a menu left open
   * follows the reader around the page.
   */
  useEffect(() => {
    const closeFromOutside = (event: Event) => {
      const menu = menuRef.current;

      if (menu?.open && !menu.contains(event.target as Node)) {
        menu.open = false;
        setIsOpen(false);
      }
    };

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && menuRef.current?.open) {
        menuRef.current.open = false;
        setIsOpen(false);
      }
    };

    document.addEventListener("pointerdown", closeFromOutside);
    document.addEventListener("keydown", closeOnEscape);

    return () => {
      document.removeEventListener("pointerdown", closeFromOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  if (!analysis) {
    return null;
  }

  async function handleDownload(reportFormat: ReportFormat) {
    if (!analysis) {
      return;
    }

    if (menuRef.current) {
      menuRef.current.open = false;
    }

    setIsOpen(false);
    setPendingFormat(reportFormat);

    try {
      const response = await fetch(
        `/proxy/reports/candidate?format=${reportFormat}`,
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
    <details
      ref={menuRef}
      className="relative"
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
    >
      <summary className="inline-flex h-10 cursor-pointer list-none items-center justify-center gap-2 rounded-lg border border-border-strong bg-surface px-4 text-sm font-medium text-text transition-colors hover:bg-surface-muted [&::-webkit-details-marker]:hidden">
        {pendingFormat ? "Preparing…" : "Download Report"}
        <ChevronIcon isOpen={isOpen} />
      </summary>

      <div className="absolute right-0 z-30 mt-2 w-44 overflow-hidden rounded-xl border border-border bg-surface py-1 shadow-[0_12px_28px_rgba(16,21,31,0.14)]">
        {(Object.keys(FORMAT_LABELS) as ReportFormat[]).map((reportFormat) => (
          <button
            key={reportFormat}
            type="button"
            disabled={pendingFormat !== null}
            onClick={() => handleDownload(reportFormat)}
            // A rule between the two rather than around them, so the menu
            // reads as one list of formats.
            className="block w-full border-b border-border px-4 py-2.5 text-left text-sm text-text transition-colors last:border-0 hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-55"
          >
            {FORMAT_LABELS[reportFormat]}
          </button>
        ))}
      </div>
    </details>
  );
}
