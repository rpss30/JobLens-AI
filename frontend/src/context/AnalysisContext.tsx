"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { AnalyzeRequest, AnalyzeResponse } from "@/lib/api/types";

export interface StoredAnalysis {
  request: AnalyzeRequest;
  response: AnalyzeResponse;
  completedAt: string;
}

interface AnalysisContextValue {
  analysis: StoredAnalysis | null;
  setAnalysis: (analysis: StoredAnalysis) => void;
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
  const [analysis, setStoredAnalysis] = useState<StoredAnalysis | null>(null);
  /*
   * Which result has already been saved. This lives beside the analysis rather
   * than inside the save button, because the button unmounts whenever the user
   * moves to another tab; keeping it there let the same result be saved twice.
   */
  const [savedCompletedAt, setSavedCompletedAt] = useState<string | null>(null);

  const setAnalysis = useCallback((nextAnalysis: StoredAnalysis) => {
    setStoredAnalysis(nextAnalysis);
    setSavedCompletedAt(null);
  }, []);

  const clearAnalysis = useCallback(() => {
    setStoredAnalysis(null);
    setSavedCompletedAt(null);
  }, []);

  const markAnalysisSaved = useCallback(() => {
    setSavedCompletedAt(analysis?.completedAt ?? null);
  }, [analysis?.completedAt]);

  const isAnalysisSaved =
    analysis !== null && savedCompletedAt === analysis.completedAt;

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
