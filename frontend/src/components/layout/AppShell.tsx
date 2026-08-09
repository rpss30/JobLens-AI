"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useState, type ReactNode } from "react";

import { DatasetSwitcher, type DatasetOption } from "@/components/layout/DatasetSwitcher";
import { SidebarNav } from "@/components/layout/SidebarNav";

interface AppShellProps {
  datasets: DatasetOption[];
  statusSlot: ReactNode;
  children: ReactNode;
}

export function AppShell({ datasets, statusSlot, children }: AppShellProps) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const pathname = usePathname();
  const [lastPathname, setLastPathname] = useState(pathname);

  // A route change, including browser back, must not leave the mobile drawer
  // covering the page. Adjusting during render avoids an extra effect pass.
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setIsMobileNavOpen(false);
  }

  return (
    <div className="min-h-dvh">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-text focus:shadow-lg"
      >
        Skip to main content
      </a>

      <header className="sticky top-0 z-30 border-b border-border bg-surface/90 backdrop-blur">
        <div className="flex h-14 items-center gap-3 px-4 sm:px-6">
          <button
            type="button"
            onClick={() => setIsMobileNavOpen((isOpen) => !isOpen)}
            aria-expanded={isMobileNavOpen}
            aria-controls="mobile-navigation"
            className="-ml-1 rounded-lg p-2 text-text-muted hover:bg-surface-muted hover:text-text lg:hidden"
          >
            <span className="sr-only">
              {isMobileNavOpen ? "Close navigation" : "Open navigation"}
            </span>
            <svg
              width="18"
              height="18"
              viewBox="0 0 18 18"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M2 4.5h14M2 9h14M2 13.5h14"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
          </button>

          <Link href="/" className="flex min-w-0 items-center">
            <span className="truncate text-xl font-semibold tracking-tight text-text sm:text-2xl">
              JobLens
            </span>
          </Link>

          <div className="ml-auto flex min-w-0 items-center gap-2 sm:gap-3">
            {/* The switcher reads the dataset from the URL, so it needs a
                boundary while search params resolve. */}
            <Suspense
              fallback={
                <div
                  className="h-9 w-[9rem] rounded-lg border border-border bg-surface-muted"
                  aria-hidden="true"
                />
              }
            >
              <DatasetSwitcher datasets={datasets} />
            </Suspense>
            {statusSlot}
          </div>
        </div>

        {isMobileNavOpen ? (
          <div
            id="mobile-navigation"
            className="border-t border-border bg-surface lg:hidden"
          >
            <SidebarNav onNavigate={() => setIsMobileNavOpen(false)} />
          </div>
        ) : null}
      </header>

      <div className="flex">
        <aside className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-56 shrink-0 border-r border-border bg-surface lg:block">
          <SidebarNav />
        </aside>

        <main id="main-content" className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl space-y-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
