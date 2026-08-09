"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
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

/*
 * Session storage is an external store, so it is read through
 * useSyncExternalStore rather than during render. The server snapshot is
 * always null, which keeps the first client render identical to the server
 * markup and avoids a hydration mismatch.
 */
const storeListeners = new Set<() => void>();

let cachedRawValue: string | null = null;
let cachedAnalysis: StoredAnalysis | null = null;

function notifyStoreListeners() {
  storeListeners.forEach((listener) => listener());
}

function subscribeToStore(listener: () => void) {
  storeListeners.add(listener);
  window.addEventListener("storage", listener);

  return () => {
    storeListeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function getStoreSnapshot(): StoredAnalysis | null {
  let rawValue: string | null = null;

  try {
    rawValue = window.sessionStorage.getItem(STORAGE_KEY);
  } catch {
    rawValue = null;
  }

  // Cache by raw string so the snapshot reference stays stable between reads.
  if (rawValue !== cachedRawValue) {
    cachedRawValue = rawValue;

    try {
      cachedAnalysis = rawValue
        ? (JSON.parse(rawValue) as StoredAnalysis)
        : null;
    } catch {
      cachedAnalysis = null;
    }
  }

  return cachedAnalysis;
}

function getServerSnapshot(): StoredAnalysis | null {
  return null;
}

export function AnalysisProvider({ children }: { children: ReactNode }) {
  const analysis = useSyncExternalStore(
    subscribeToStore,
    getStoreSnapshot,
    getServerSnapshot,
  );

  const setAnalysis = useCallback((nextAnalysis: StoredAnalysis) => {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextAnalysis));
    } catch {
      // A full or unavailable session store should not break the analysis.
    }

    notifyStoreListeners();
  }, []);

  const clearAnalysis = useCallback(() => {
    try {
      window.sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Nothing to recover from; the next snapshot read returns null.
    }

    notifyStoreListeners();
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
