"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/context/ToastContext";
import { saveAnalysisRun } from "@/lib/analysisRuns";
import type { AnalyzeRequest, AnalyzeResponse } from "@/lib/api/types";

export interface StoredAnalysis {
  request: AnalyzeRequest;
  response: AnalyzeResponse;
  completedAt: string;
}

interface AnalysisContextValue {
  analysis: StoredAnalysis | null;
  /**
   * Set alreadySaved for a result that came back out of history: it is the
   * same run, so offering to save it again would only duplicate it.
   */
  setAnalysis: (
    analysis: StoredAnalysis,
    options?: { alreadySaved?: boolean },
  ) => void;
  /** Asks first when the result would be lost unsaved. */
  clearAnalysis: () => void;
  /** True once the current result has been written to history. */
  isAnalysisSaved: boolean;
  markAnalysisSaved: () => void;
}

const AnalysisContext = createContext<AnalysisContextValue | null>(null);

/**
 * Holds the most recent result so Overview, Jobs, and Skills can share it while
 * moving between pages.
 *
 * This is deliberately in-memory only. It was session storage first, but that
 * meant a reload dropped someone back into stale results with no obvious way
 * back to the starting page. Keeping it in memory means a reload, or the
 * JobLens wordmark, always returns to the first-run state.
 */
export function AnalysisProvider({ children }: { children: ReactNode }) {
  const { showToast } = useToast();
  const [analysis, setStoredAnalysis] = useState<StoredAnalysis | null>(null);
  /*
   * Which result has already been saved. This lives beside the analysis rather
   * than inside the save button, because the button unmounts whenever the user
   * moves to another tab; keeping it there let the same result be saved twice.
   */
  const [savedCompletedAt, setSavedCompletedAt] = useState<string | null>(null);
  const [isConfirmingClear, setIsConfirmingClear] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const isAnalysisSaved =
    analysis !== null && savedCompletedAt === analysis.completedAt;

  const setAnalysis = useCallback(
    (nextAnalysis: StoredAnalysis, options?: { alreadySaved?: boolean }) => {
      setStoredAnalysis(nextAnalysis);
      /*
       * Set from the incoming result rather than through markAnalysisSaved,
       * which reads the analysis in scope when it was made and would mark the
       * one being replaced.
       */
      setSavedCompletedAt(
        options?.alreadySaved ? nextAnalysis.completedAt : null,
      );
    },
    [],
  );

  const discardAnalysis = useCallback(() => {
    setStoredAnalysis(null);
    setSavedCompletedAt(null);
    setIsConfirmingClear(false);
  }, []);

  const clearAnalysis = useCallback(() => {
    // Nothing to lose: no result, or one already in history.
    if (analysis === null || isAnalysisSaved) {
      discardAnalysis();
      return;
    }

    setIsConfirmingClear(true);
  }, [analysis, isAnalysisSaved, discardAnalysis]);

  const markAnalysisSaved = useCallback(() => {
    setSavedCompletedAt(analysis?.completedAt ?? null);
  }, [analysis?.completedAt]);

  /*
   * A reload or a closed tab takes the result with it, and the browser will
   * only ask on our behalf while something is genuinely unsaved.
   */
  useEffect(() => {
    if (analysis === null || isAnalysisSaved) {
      return;
    }

    const warnBeforeLeaving = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      // Deprecated, and still what some browsers actually read.
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", warnBeforeLeaving);

    return () => window.removeEventListener("beforeunload", warnBeforeLeaving);
  }, [analysis, isAnalysisSaved]);

  async function saveThenClear() {
    if (!analysis) {
      return;
    }

    setIsSaving(true);

    const error = await saveAnalysisRun(analysis);

    setIsSaving(false);

    if (error) {
      showToast(error, "error");
      return;
    }

    showToast("Saved to your history.");
    discardAnalysis();
  }

  const value = useMemo(
    () => ({
      analysis,
      setAnalysis,
      clearAnalysis,
      isAnalysisSaved,
      markAnalysisSaved,
    }),
    [analysis, setAnalysis, clearAnalysis, isAnalysisSaved, markAnalysisSaved],
  );

  return (
    <AnalysisContext.Provider value={value}>
      {children}

      {/* Here rather than beside any one button, because every way of losing
          a result ends up calling clearAnalysis. */}
      <ConfirmDialog
        open={isConfirmingClear}
        title="Save this result first?"
        description="This result is not in your history yet. Starting again will lose it."
        confirmLabel="Save and continue"
        alternativeLabel="Discard"
        isBusy={isSaving}
        onConfirm={saveThenClear}
        onAlternative={discardAnalysis}
        onCancel={() => setIsConfirmingClear(false)}
      />
    </AnalysisContext.Provider>
  );
}

export function useAnalysis(): AnalysisContextValue {
  const context = useContext(AnalysisContext);

  if (!context) {
    throw new Error("useAnalysis must be used inside an AnalysisProvider.");
  }

  return context;
}
