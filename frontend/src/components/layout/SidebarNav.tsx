"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { ChevronIcon } from "@/components/layout/NavIcons";
import { useDatasetParam } from "@/components/layout/ShellSearchParams";
import { cn } from "@/lib/cn";
import { withDataset } from "@/lib/datasets";
import { isActiveRoute, navigationItems } from "@/lib/navigation";

export function SidebarNav({
  onNavigate,
  isCollapsed = false,
}: {
  onNavigate?: () => void;
  /** Icons only, for the narrow rail the collapse button leaves behind. */
  isCollapsed?: boolean;
}) {
  const pathname = usePathname();
  const datasetName = useDatasetParam();
  const isInsideMarketInsights = pathname.startsWith("/skills");
  /*
   * Expanded, the section opens itself when you are inside it and can then be
   * closed by hand: deriving it from the route alone would take the toggle
   * away, and pure state would hide where you currently are.
   *
   * On a rail it never opens itself. The same state draws a flyout over the
   * page there, and one of those covering the page on arrival is something
   * nobody asked for.
   */
  const [isMarketInsightsOpen, setIsMarketInsightsOpen] = useState(
    isInsideMarketInsights && !isCollapsed,
  );
  const [lastSectionState, setLastSectionState] = useState(
    isInsideMarketInsights,
  );
  const [lastPathname, setLastPathname] = useState(pathname);
  const [lastCollapsed, setLastCollapsed] = useState(isCollapsed);

  if (isInsideMarketInsights !== lastSectionState) {
    setLastSectionState(isInsideMarketInsights);
    setIsMarketInsightsOpen(isInsideMarketInsights && !isCollapsed);
  }

  /*
   * A flyout has to shut once it has taken you somewhere, and folding the
   * sidebar away must not leave one hanging over the page. Expanded the
   * section is part of the sidebar and stays open, which is how you see
   * where you are.
   */
  if (pathname !== lastPathname || isCollapsed !== lastCollapsed) {
    setLastPathname(pathname);
    setLastCollapsed(isCollapsed);

    if (isCollapsed) {
      setIsMarketInsightsOpen(false);
    }
  }

  return (
    <nav
      aria-label="Primary"
      className={cn("py-2", isCollapsed ? "px-2.5" : "px-3")}
    >
      <ul className="space-y-1">
        {navigationItems.map(({ href, label, Icon, children }) => {
          // Matching uses the bare path: the dataset only rides along in the
          // query and never decides which item is current.
          const isActive = isActiveRoute(pathname, href);
          const isExpanded = Boolean(children) && isMarketInsightsOpen;

          return (
            <li key={href} className="relative">
              {/*
                A parent with children only opens and closes them. It used to
                navigate as well, so one click both moved you and expanded the
                section, and there was no way to peek at the views from
                elsewhere without leaving the page you were on.
              */}
              {children ? (
                <button
                  type="button"
                  aria-expanded={isExpanded}
                  aria-controls="market-insights-views"
                  onClick={() => setIsMarketInsightsOpen((open) => !open)}
                  className={cn(
                    "peer flex w-full items-center gap-3 rounded-xl py-2.5 text-base font-medium transition-colors",
                    isCollapsed ? "justify-center px-0" : "px-3",
                    isActive
                      ? "bg-accent-fill text-on-accent"
                      : "text-text-muted hover:bg-surface-muted hover:text-text",
                  )}
                >
                  <Icon className="shrink-0" />
                  {isCollapsed ? (
                    <span className="sr-only">{label}</span>
                  ) : (
                    <>
                      <span className="flex-1 text-left">{label}</span>
                      <ChevronIcon
                        className={cn(
                          "shrink-0 transition-transform",
                          isExpanded && "rotate-180",
                        )}
                      />
                    </>
                  )}
                </button>
              ) : (
                <Link
                  href={withDataset(href, datasetName)}
                  onClick={onNavigate}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "peer flex items-center gap-3 rounded-xl py-2.5 text-base font-medium transition-colors",
                    isCollapsed ? "justify-center px-0" : "px-3",
                    isActive
                      ? "bg-accent-fill text-on-accent"
                      : "text-text-muted hover:bg-surface-muted hover:text-text",
                  )}
                >
                  <Icon className="shrink-0" />
                  {isCollapsed ? <span className="sr-only">{label}</span> : label}
                </Link>
              )}

              {/* A rail shows marks and no words, so the word arrives beside
                  the mark it belongs to. Not while the section's own views
                  are open in the same place. */}
              {isCollapsed && !isExpanded ? (
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 -translate-y-1/2 whitespace-nowrap rounded-lg bg-text px-2.5 py-1.5 text-xs font-medium text-surface opacity-0 shadow-[0_8px_20px_rgba(16,21,31,0.18)] transition-opacity peer-hover:opacity-100 peer-focus-visible:opacity-100"
                >
                  {label}
                </span>
              ) : null}

              {children && isExpanded ? (
                <ul
                  id="market-insights-views"
                  className={cn(
                    isCollapsed
                      ? "absolute left-full top-0 z-40 ml-2 w-56 rounded-xl border border-border bg-surface p-1.5 shadow-[0_12px_28px_rgba(16,21,31,0.14)]"
                      : "mt-1 space-y-0.5 pl-8",
                  )}
                >
                  {children.map((child) => {
                    // Exact match: every child lives under the parent path, so
                    // startsWith would light them all up at once.
                    const isChildActive = pathname === child.href;

                    return (
                      <li key={child.href}>
                        <Link
                          href={withDataset(child.href, datasetName)}
                          onClick={onNavigate}
                          aria-current={isChildActive ? "page" : undefined}
                          className={cn(
                            "block rounded-lg px-3 py-2 text-[0.9375rem] transition-colors",
                            isChildActive
                              ? "bg-accent-soft font-medium text-accent"
                              : "text-text-muted hover:bg-surface-muted hover:text-text",
                          )}
                        >
                          {child.label}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              ) : null}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
