import type { ReactNode } from "react";

import { AvatarIcon, ChevronIcon } from "@/components/layout/NavIcons";
import {
  DatasetSwitcher,
  type DatasetOption,
} from "@/components/layout/DatasetSwitcher";

interface SidebarFooterProps {
  datasets: DatasetOption[];
  statusSlot: ReactNode;
  /** The rail keeps the account mark and drops everything that needs words. */
  isCollapsed?: boolean;
}

/**
 * The design has no top bar, so the controls that used to live there — the
 * dataset switcher and the backend status indicator — sit at the foot of the
 * sidebar instead, above the account block.
 */
export function SidebarFooter({
  datasets,
  statusSlot,
  isCollapsed = false,
}: SidebarFooterProps) {
  if (isCollapsed) {
    return (
      <div className="flex justify-center border-t border-border px-2 py-3.5">
        <AvatarIcon className="shrink-0 text-text-muted" />
      </div>
    );
  }

  return (
    <div>
      <div className="space-y-2.5 border-t border-border px-4 py-3.5">
        <DatasetSwitcher datasets={datasets} />
        {statusSlot}
      </div>

      {/*
        JobLens has no accounts. This block is a static placeholder for the
        shape of the design and is deliberately inert: it is not a button, and
        the chevron is decorative.
      */}
      <div className="flex items-center gap-3 border-t border-border px-4 py-3.5">
        <AvatarIcon className="shrink-0 text-text-muted" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-medium text-text">Username</p>
          <p className="truncate text-xs font-medium text-text-muted">
            user@something.com
          </p>
        </div>
        <ChevronIcon className="shrink-0 text-text-subtle" />
      </div>
    </div>
  );
}
