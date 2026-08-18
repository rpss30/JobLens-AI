"use client";

import { useSearchParams } from "next/navigation";
import {
  Suspense,
  createContext,
  useContext,
  type ReactNode,
} from "react";

type ShellSearchParams = URLSearchParams | null;

const ShellSearchParamsContext = createContext<ShellSearchParams>(null);

/** The query the shell was rendered with, or null before it resolves. */
export function useShellSearchParams(): ShellSearchParams {
  return useContext(ShellSearchParamsContext);
}

/** The active dataset, which every link in the shell has to carry. */
export function useDatasetParam(): string | null {
  return useShellSearchParams()?.get("dataset") ?? null;
}

function Reader({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();

  return (
    <ShellSearchParamsContext.Provider value={searchParams}>
      {children}
    </ShellSearchParamsContext.Provider>
  );
}

/**
 * Reads the query once for the whole shell.
 *
 * useSearchParams suspends until the request's query is known, so each caller
 * needs a boundary. Calling it from the wordmark, the nav and the dataset
 * switcher separately put four boundaries in the layout, and React left one of
 * them showing its fallback for good: the resolved markup stayed parked in a
 * template and never swapped in, so the sidebar rendered stale links and the
 * switcher vanished entirely on /jobs.
 *
 * One reader, one boundary. The fallback renders the same children with a null
 * query, so the shell stays visible and usable while the query resolves.
 */
export function ShellSearchParamsProvider({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <Suspense fallback={children}>
      <Reader>{children}</Reader>
    </Suspense>
  );
}
