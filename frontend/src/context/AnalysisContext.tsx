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

const STORAGE_KEY = "joblens.analysis";

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
 * Holds the most recent analysis so Overview, Jobs, and Skills can read one
 * result without re-running it. Session storage keeps it across navigation and
 * reloads without persisting anything to a server.
 */
function readStoredAnalysis(): StoredAnalysis | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const rawValue = window.sessionStorage.getItem(STORAGE_KEY);

    return rawValue ? (JSON.parse(rawValue) as StoredAnalysis) : null;
  } catch {
    return null;
  }
}

export function AnalysisProvider({ children }: { children: ReactNode }) {
  // Lazy initialiser runs on the client only, so hydration stays consistent.
  const [analysis, setStoredAnalysis] = useState<StoredAnalysis | null>(null);
  const [isHydrated, setIsHydrated] = useState(false);

  if (!isHydrated && typeof window !== "undefined") {
    setIsHydrated(true);
    setStoredAnalysis(readStoredAnalysis());
  }

  const setAnalysis = useCallback((nextAnalysis: StoredAnalysis) => {
    setStoredAnalysis(nextAnalysis);

    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextAnalysis));
    } catch {
      // A full or unavailable session store should not break the analysis.
    }
  }, []);

  const clearAnalysis = useCallback(() => {
    setStoredAnalysis(null);

    try {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Nothing to recover from; the in-memory value is already cleared.
    }
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
