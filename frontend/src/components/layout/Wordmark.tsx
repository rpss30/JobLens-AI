"use client";

import Link from "next/link";

import { LogoMark } from "@/components/layout/NavIcons";
import { useDatasetParam } from "@/components/layout/ShellSearchParams";
import { useAnalysis } from "@/context/AnalysisContext";
import { withDataset } from "@/lib/datasets";

/**
 * A way back to a clean start: it clears the current result rather than
 * returning to a stale one, but keeps the chosen dataset, which is a setting
 * rather than part of the result.
 */
export function Wordmark({ isCollapsed = false }: { isCollapsed?: boolean }) {
  const { clearAnalysis } = useAnalysis();
  const datasetName = useDatasetParam();

  return (
    <Link
      href={withDataset("/", datasetName)}
      onClick={clearAnalysis}
      className={
        isCollapsed
          ? "flex justify-center"
          : "flex min-w-0 items-center gap-3"
      }
    >
      <LogoMark className="shrink-0 text-text" />
      {/* The mark alone on a rail, but the name still has to be readable to
          anything that is not looking at it. */}
      <span
        className={
          isCollapsed
            ? "sr-only"
            : "truncate text-4xl font-semibold tracking-tight text-text"
        }
      >
        JobLens
      </span>
    </Link>
  );
}
