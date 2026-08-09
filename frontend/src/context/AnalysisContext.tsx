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

  const setAnalysis = useCallback((nextAnalysis: StoredAnalysis) => {
    setStoredAnalysis(nextAnalysis);
  }, []);

  const clearAnalysis = useCallback(() => {
    setStoredAnalysis(null);
  }, []);

  const value = useMemo(
    () => ({ analysis, setAnalysis, clearAnalysis }),
    [analysis, setAnalysis, clearAnalysis],
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
