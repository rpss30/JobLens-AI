import type { ComponentType } from "react";

import {
  AnalyzeIcon,
  DatasetsIcon,
  HistoryIcon,
  JobsIcon,
  OverviewIcon,
  SkillsIcon,
} from "@/components/layout/NavIcons";

export interface NavChild {
  href: string;
  label: string;
}

export interface NavItem {
  href: string;
  label: string;
  Icon: ComponentType<{ className?: string }>;
  children?: NavChild[];
}

// Market Insights is one dataset viewed four ways, so its views are children
// rather than four more top-level entries.
const marketInsightsChildren: NavChild[] = [
  { href: "/skills", label: "Skills Demand" },
  // Role skills and role distribution read the same categories two ways, so
  // they share one view rather than splitting it.
  { href: "/skills/role-distribution", label: "Role Distribution" },
  { href: "/skills/locations", label: "Job Locations" },
  { href: "/skills/companies", label: "Top Hiring Companies" },
];

export const navigationItems: NavItem[] = [
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

export function isActiveRoute(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export interface NavDestination {
  href: string;
  label: string;
  /** The section it sits under, for a child; empty for a top-level view. */
  section: string;
  Icon: ComponentType<{ className?: string }>;
}

/**
 * Every view the search can take you to, flattened.
 *
 * A parent with children is not itself a destination: its own row only opens
 * the section in the sidebar, so offering it here would lead somewhere the
 * sidebar will not.
 */
export const navDestinations: NavDestination[] = navigationItems.flatMap(
  (item) =>
    item.children
      ? item.children.map((child) => ({
          href: child.href,
          label: child.label,
          section: item.label,
          Icon: item.Icon,
        }))
      : [{ href: item.href, label: item.label, section: "", Icon: item.Icon }],
);

/** Matches on the view's own name first, then the section it belongs to. */
export function searchDestinations(query: string): NavDestination[] {
  const needle = query.trim().toLowerCase();

  if (!needle) {
    return [];
  }

  const scored = navDestinations
    .map((destination) => {
      const label = destination.label.toLowerCase();
      const section = destination.section.toLowerCase();

      if (label.startsWith(needle)) {
        return { destination, rank: 0 };
      }

      if (label.includes(needle)) {
        return { destination, rank: 1 };
      }

      if (section.includes(needle)) {
        return { destination, rank: 2 };
      }

      return null;
    })
    .filter((entry) => entry !== null);

  return scored
    .sort((first, second) => first.rank - second.rank)
    .map((entry) => entry.destination);
}
