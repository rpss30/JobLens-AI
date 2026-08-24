"use client";

import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

import { CloseIcon, MenuIcon, MoreIcon } from "@/components/layout/NavIcons";
import { NavSearch } from "@/components/layout/NavSearch";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { SidebarFooter } from "@/components/layout/SidebarFooter";
import { ShellSearchParamsProvider } from "@/components/layout/ShellSearchParams";
import { SidebarNav } from "@/components/layout/SidebarNav";
import { TopBar } from "@/components/layout/TopBar";
import { Wordmark } from "@/components/layout/Wordmark";
import type { DatasetOption } from "@/components/layout/DatasetSwitcher";
import { rememberSidebar, type Theme } from "@/lib/theme";

interface AppShellProps {
  datasets: DatasetOption[];
  statusSlot: ReactNode;
  /** Both read from the request, so the first paint is already correct. */
  initialTheme: Theme | null;
  initialSidebarCollapsed: boolean;
  children: ReactNode;
}

export function AppShell({
  datasets,
  statusSlot,
  initialTheme,
  initialSidebarCollapsed,
  children,
}: AppShellProps) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  /*
   * The search and the light switch live behind this on a phone: the bar has
   * room for the wordmark and two controls, and neither of those is something
   * you reach for on the way to somewhere.
   */
  const [isMobileToolsOpen, setIsMobileToolsOpen] = useState(false);
  // Seeded from the cookie the server already rendered against, so the rail
  // never starts wide and snaps shut.
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(
    initialSidebarCollapsed,
  );
  const pathname = usePathname();
  const [lastPathname, setLastPathname] = useState(pathname);

  // A route change, including browser back, must not leave the mobile drawer
  // covering the page. Adjusting during render avoids an extra effect pass.
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setIsMobileNavOpen(false);
    setIsMobileToolsOpen(false);
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
        {/* Below lg the sidebar head becomes a bar, and the rest of it a
            drawer that slides over the page rather than pushing it down. */}
        <header className="sticky top-0 z-50 border-b border-border bg-surface lg:hidden">
          <div className="flex h-16 items-center gap-3 px-4">
            <button
              type="button"
              onClick={() => {
                // One panel at a time: both hang off the same bar, and the
                // drawer starts below it, so an open tools row would push
                // the first nav item out of sight.
                setIsMobileToolsOpen(false);
                setIsMobileNavOpen((isOpen) => !isOpen);
              }}
              aria-expanded={isMobileNavOpen}
              aria-controls="mobile-navigation"
              className={`-ml-1 shrink-0 rounded-lg p-2 transition-colors ${
                isMobileNavOpen
                  ? "bg-surface-muted text-text"
                  : "text-text hover:bg-surface-muted"
              }`}
            >
              <span className="sr-only">
                {isMobileNavOpen ? "Close navigation" : "Open navigation"}
              </span>
              {isMobileNavOpen ? <CloseIcon /> : <MenuIcon />}
            </button>

            {/* Centred between the two controls rather than pinned left. */}
            <div className="flex min-w-0 flex-1 justify-center">
              <Wordmark />
            </div>

            <button
              type="button"
              onClick={() => {
                setIsMobileNavOpen(false);
                setIsMobileToolsOpen((isOpen) => !isOpen);
              }}
              aria-expanded={isMobileToolsOpen}
              aria-controls="mobile-tools"
              className={`-mr-1 shrink-0 rounded-lg p-2 transition-colors ${
                isMobileToolsOpen
                  ? "bg-surface-muted text-text"
                  : "text-text hover:bg-surface-muted"
              }`}
            >
              <span className="sr-only">
                {isMobileToolsOpen
                  ? "Hide search and appearance"
                  : "Show search and appearance"}
              </span>
              <MoreIcon />
            </button>
          </div>

          {/*
           * Always rendered, opened by growing its row from nothing. Mounting
           * on the toggle would give it no closing to animate, and a height
           * this can only know at runtime is what a 0fr-to-1fr row is for.
           */}
          <div
            id="mobile-tools"
            inert={!isMobileToolsOpen}
            className={`grid overflow-hidden duration-200 ease-out motion-safe:transition-[grid-template-rows] ${
              isMobileToolsOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
            }`}
          >
            <div className="min-h-0 overflow-hidden">
              <div className="flex items-center gap-3 border-t border-border px-4 py-3">
                <NavSearch />
                <ThemeToggle initialTheme={initialTheme} />
              </div>
            </div>
          </div>
        </header>

        {/* The page stays put underneath and is dimmed, rather than being
            pushed down the length of the whole menu. Both parts stay mounted
            so the drawer slides back out rather than vanishing. */}
        <button
          type="button"
          tabIndex={isMobileNavOpen ? 0 : -1}
          aria-label="Close navigation"
          onClick={() => setIsMobileNavOpen(false)}
          className={`fixed inset-0 top-16 z-30 bg-text/40 duration-200 motion-safe:transition-opacity lg:hidden ${
            isMobileNavOpen
              ? "opacity-100"
              : "pointer-events-none opacity-0"
          }`}
        />
        <div
          id="mobile-navigation"
          inert={!isMobileNavOpen}
          className={`fixed bottom-0 left-0 top-16 z-40 flex w-64 flex-col border-r border-border bg-surface duration-200 ease-out motion-safe:transition-transform lg:hidden ${
            isMobileNavOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="flex-1 overflow-y-auto py-2">
            <SidebarNav onNavigate={() => setIsMobileNavOpen(false)} />
          </div>
          {footer}
        </div>

        <aside
          // Above the main column, not just before it: sticky makes this a
          // stacking context, so the flyout's own z-index cannot lift it out.
          className={`sticky top-0 z-40 hidden h-dvh shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200 lg:flex ${
            isSidebarCollapsed ? "w-[4.5rem]" : "w-64"
          }`}
        >
          <div
            className={
              isSidebarCollapsed ? "px-2 py-5" : "px-4 py-5"
            }
          >
            <Wordmark isCollapsed={isSidebarCollapsed} />
          </div>
          {/* A rail is short enough not to need scrolling, and scrolling it
              would clip the flyout the Market Insights icon opens. */}
          <div
            className={isSidebarCollapsed ? "flex-1" : "flex-1 overflow-y-auto"}
          >
            <SidebarNav isCollapsed={isSidebarCollapsed} />
          </div>
          <SidebarFooter
            datasets={datasets}
            statusSlot={statusSlot}
            isCollapsed={isSidebarCollapsed}
          />
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar
            isSidebarCollapsed={isSidebarCollapsed}
            initialTheme={initialTheme}
            onToggleSidebar={() => {
              setIsSidebarCollapsed(!isSidebarCollapsed);
              rememberSidebar(!isSidebarCollapsed);
            }}
          />

          <main
            id="main-content"
            className="min-w-0 flex-1 px-5 py-8 sm:px-8 lg:px-10 lg:py-10"
          >
            <div className="mx-auto max-w-7xl space-y-8">{children}</div>
          </main>
        </div>
      </ShellSearchParamsProvider>
    </div>
  );
}
