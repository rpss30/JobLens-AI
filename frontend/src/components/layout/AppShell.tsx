"use client";

import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

import { MenuIcon } from "@/components/layout/NavIcons";
import { SidebarFooter } from "@/components/layout/SidebarFooter";
import { ShellSearchParamsProvider } from "@/components/layout/ShellSearchParams";
import { SidebarNav } from "@/components/layout/SidebarNav";
import { Wordmark } from "@/components/layout/Wordmark";
import type { DatasetOption } from "@/components/layout/DatasetSwitcher";

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

  const footer = <SidebarFooter datasets={datasets} statusSlot={statusSlot} />;

  return (
    <div className="min-h-dvh lg:flex">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-text focus:shadow-lg"
      >
        Skip to main content
      </a>

      {/* The provider wraps the chrome only. Keeping the page outside it
          means a suspended query never re-renders the whole route. */}
      <ShellSearchParamsProvider>
        {/* Below lg the sidebar head becomes a bar and the rest of it a drawer. */}
        <header className="sticky top-0 z-30 border-b border-border bg-surface lg:hidden">
          <div className="flex h-16 items-center gap-3 px-4">
            <button
              type="button"
              onClick={() => setIsMobileNavOpen((isOpen) => !isOpen)}
              aria-expanded={isMobileNavOpen}
              aria-controls="mobile-navigation"
              className="-ml-1 rounded-lg p-2 text-text-muted hover:bg-surface-muted hover:text-text"
            >
              <span className="sr-only">
                {isMobileNavOpen ? "Close navigation" : "Open navigation"}
              </span>
              <MenuIcon />
            </button>
            <Wordmark />
          </div>

          {isMobileNavOpen ? (
            <div id="mobile-navigation" className="border-t border-border pb-1">
              <SidebarNav onNavigate={() => setIsMobileNavOpen(false)} />
              {footer}
            </div>
          ) : null}
        </header>

        <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col border-r border-border bg-surface lg:flex">
          <div className="px-4 py-5">
            <Wordmark />
          </div>
          <div className="flex-1 overflow-y-auto">
            <SidebarNav />
          </div>
          {footer}
        </aside>
      </ShellSearchParamsProvider>

      <main
        id="main-content"
        className="min-w-0 flex-1 px-5 py-8 sm:px-8 lg:px-10 lg:py-10"
      >
        <div className="mx-auto max-w-7xl space-y-8">{children}</div>
      </main>
    </div>
  );
}
