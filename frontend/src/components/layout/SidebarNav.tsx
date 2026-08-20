"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import {
  AnalyzeIcon,
  ChevronIcon,
  DatasetsIcon,
  HistoryIcon,
  JobsIcon,
  OverviewIcon,
  SkillsIcon,
} from "@/components/layout/NavIcons";
import { useDatasetParam } from "@/components/layout/ShellSearchParams";
import { cn } from "@/lib/cn";
import { withDataset } from "@/lib/datasets";

// Market Insights is one dataset viewed four ways, so its views are children
// rather than four more top-level entries.
const marketInsightsChildren = [
  { href: "/skills", label: "Skills Demand" },
  // Role skills and role distribution read the same categories two ways, so
  // they share one view rather than splitting it.
  { href: "/skills/role-distribution", label: "Role Distribution" },
  { href: "/skills/locations", label: "Job Locations" },
  { href: "/skills/companies", label: "Top Hiring Companies" },
];

const navigationItems = [
  { href: "/", label: "Overview", Icon: OverviewIcon },
  { href: "/analyze", label: "Analyze", Icon: AnalyzeIcon },
  { href: "/jobs", label: "Jobs", Icon: JobsIcon },
  {
    href: "/skills",
    label: "Market Insights",
    Icon: SkillsIcon,
    children: marketInsightsChildren,
  },
  { href: "/history", label: "History", Icon: HistoryIcon },
  { href: "/datasets", label: "Datasets", Icon: DatasetsIcon },
];

function isActiveRoute(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const datasetName = useDatasetParam();
  const isInsideMarketInsights = pathname.startsWith("/skills");
  /*
   * Opens itself when you are inside the section, and can then be closed by
   * hand. Deriving it from the route alone would take the toggle away; keeping
   * it purely in state would hide where you currently are.
   */
  const [isMarketInsightsOpen, setIsMarketInsightsOpen] = useState(
    isInsideMarketInsights,
  );
  const [lastSectionState, setLastSectionState] = useState(
    isInsideMarketInsights,
  );

  if (isInsideMarketInsights !== lastSectionState) {
    setLastSectionState(isInsideMarketInsights);
    setIsMarketInsightsOpen(isInsideMarketInsights);
  }

  return (
    <nav aria-label="Primary" className="px-3 py-2">
      <ul className="space-y-1">
        {navigationItems.map(({ href, label, Icon, children }) => {
          // Matching uses the bare path: the dataset only rides along in the
          // query and never decides which item is current.
          const isActive = isActiveRoute(pathname, href);
          const isExpanded = Boolean(children) && isMarketInsightsOpen;

          return (
            <li key={href}>
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
                    "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-base font-medium transition-colors",
                    isActive
                      ? "bg-accent-fill text-on-accent"
                      : "text-text-muted hover:bg-surface-muted hover:text-text",
                  )}
                >
                  <Icon className="shrink-0" />
                  <span className="flex-1 text-left">{label}</span>
                  <ChevronIcon
                    className={cn(
                      "shrink-0 transition-transform",
                      isExpanded && "rotate-180",
                    )}
                  />
                </button>
              ) : (
                <Link
                  href={withDataset(href, datasetName)}
                  onClick={onNavigate}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-base font-medium transition-colors",
                    isActive
                      ? "bg-accent-fill text-on-accent"
                      : "text-text-muted hover:bg-surface-muted hover:text-text",
                  )}
                >
                  <Icon className="shrink-0" />
                  {label}
                </Link>
              )}

              {children && isExpanded ? (
                <ul
                  id="market-insights-views"
                  className="mt-1 space-y-0.5 pl-8"
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
