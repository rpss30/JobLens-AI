import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface StatTileProps {
  label: string;
  value: string;
  hint?: string;
  emphasis?: boolean;
  children?: ReactNode;
}

export function StatTile({
  label,
  value,
  hint,
  emphasis = false,
  children,
}: StatTileProps) {
  return (
    <div className="rounded-xl border border-border bg-surface px-5 py-4">
      <p className="text-xs font-medium uppercase tracking-wide text-text-subtle">
        {label}
      </p>
      <p
        className={cn(
          "mt-2 font-semibold tracking-tight text-text",
          emphasis ? "text-3xl" : "text-2xl",
        )}
        // Long role names must not blow out the tile on narrow screens.
        title={value}
      >
        {value}
      </p>
      {hint ? <p className="mt-1 text-sm text-text-muted">{hint}</p> : null}
      {children ? <div className="mt-3">{children}</div> : null}
    </div>
  );
}
