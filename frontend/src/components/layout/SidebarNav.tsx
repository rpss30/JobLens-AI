"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";

const navigationItems = [
  { href: "/", label: "Overview" },
  { href: "/analyze", label: "Analyze" },
  { href: "/jobs", label: "Jobs" },
  { href: "/skills", label: "Skills & Market" },
  { href: "/history", label: "History" },
];

// Dataset management is reachable from the top bar on wider screens, so the
// mobile drawer carries it instead of adding a sixth primary area.
const secondaryItems = [{ href: "/datasets", label: "Datasets" }];

function isActiveRoute(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const items = [...navigationItems, ...secondaryItems];

  return (
    <nav aria-label="Primary" className="p-3">
      <ul className="space-y-0.5">
        {items.map((item) => {
          const isActive = isActiveRoute(pathname, item.href);

          return (
            <li key={item.href}>
              <Link
                href={item.href}
                onClick={onNavigate}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "block rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-text-muted hover:bg-surface-muted hover:text-text",
                )}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
