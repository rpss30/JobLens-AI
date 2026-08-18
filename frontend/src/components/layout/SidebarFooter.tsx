import { Suspense, type ReactNode } from "react";

import { AvatarIcon, ChevronIcon } from "@/components/layout/NavIcons";
import {
  DatasetSwitcher,
  type DatasetOption,
} from "@/components/layout/DatasetSwitcher";

interface SidebarFooterProps {
  datasets: DatasetOption[];
  statusSlot: ReactNode;
}

/**
 * The design has no top bar, so the controls that used to live there — the
 * dataset switcher and the backend status indicator — sit at the foot of the
 * sidebar instead, above the account block.
 */
export function SidebarFooter({ datasets, statusSlot }: SidebarFooterProps) {
  return (
    <div>
      <div className="space-y-2.5 border-t border-border px-4 py-3.5">
        {/* The switcher reads the dataset from the URL, so it needs a boundary
            while search params resolve. Only it suspends, so the rest of the
            footer keeps its height and the sidebar does not shift. */}
        <Suspense
          fallback={
            <div className="space-y-1.5">
              <span className="block text-xs font-medium text-text-subtle">
                Dataset
              </span>
              <div
                className="h-9 w-full rounded-lg border border-border bg-surface-muted"
                aria-hidden="true"
              />
            </div>
          }
        >
          <DatasetSwitcher datasets={datasets} />
        </Suspense>
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
          <p className="truncate text-sm font-semibold text-text">Username</p>
          <p className="truncate text-xs text-text-muted">
            user@something.com
          </p>
        </div>
        <ChevronIcon className="shrink-0 text-text-subtle" />
      </div>
    </div>
  );
}
