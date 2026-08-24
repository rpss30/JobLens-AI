"use client";

import { CollapseIcon, ExpandIcon } from "@/components/layout/NavIcons";
import { NavSearch } from "@/components/layout/NavSearch";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import type { Theme } from "@/lib/theme";

/**
 * The bar over the page: a way to put the sidebar away, a way to reach any
 * view, and the light or dark switch.
 *
 * It sits in the main column rather than across the whole window, so the
 * sidebar keeps its own head and the two read as one row.
 */
export function TopBar({
  isSidebarCollapsed,
  initialTheme,
  onToggleSidebar,
}: {
  isSidebarCollapsed: boolean;
  initialTheme: Theme | null;
  onToggleSidebar: () => void;
}) {
  return (
    <header className="sticky top-0 z-30 hidden border-b border-border bg-surface lg:block">
      <div className="flex h-16 items-center gap-4 px-6">
        <button
          type="button"
          onClick={onToggleSidebar}
          aria-expanded={!isSidebarCollapsed}
          aria-label={
            isSidebarCollapsed ? "Expand the sidebar" : "Collapse the sidebar"
          }
          title={
            isSidebarCollapsed ? "Expand the sidebar" : "Collapse the sidebar"
          }
          className="inline-flex size-10 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-text-muted transition-colors hover:bg-surface-muted hover:text-text"
        >
          {isSidebarCollapsed ? <ExpandIcon /> : <CollapseIcon />}
        </button>

        <NavSearch />

        <div className="ml-auto">
          <ThemeToggle initialTheme={initialTheme} />
        </div>
      </div>
    </header>
  );
}
