"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  AnalyzeIcon,
  DatasetsIcon,
  HistoryIcon,
  JobsIcon,
  OverviewIcon,
  SkillsIcon,
} from "@/components/layout/NavIcons";
import { useDatasetParam } from "@/components/layout/ShellSearchParams";
import { cn } from "@/lib/cn";
import { withDataset } from "@/lib/datasets";

const navigationItems = [
  { href: "/", label: "Overview", Icon: OverviewIcon },
  { href: "/analyze", label: "Analyze", Icon: AnalyzeIcon },
  { href: "/jobs", label: "Jobs", Icon: JobsIcon },
  { href: "/skills", label: "Skills & Market", Icon: SkillsIcon },
  { href: "/history", label: "History", Icon: HistoryIcon },
  { href: "/datasets", label: "Datasets", Icon: DatasetsIcon },
];

function isActiveRoute(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const datasetName = useDatasetParam();

  return (
    <nav aria-label="Primary" className="px-3 py-2">
      <ul className="space-y-1">
        {navigationItems.map(({ href, label, Icon }) => {
          // Matching uses the bare path: the dataset only rides along in the
          // query and never decides which item is current.
          const isActive = isActiveRoute(pathname, href);

          return (
            <li key={href}>
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
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
