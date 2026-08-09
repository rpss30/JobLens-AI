import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border-strong bg-surface px-6 py-12 text-center",
        className,
      )}
    >
      <h3 className="text-base font-semibold text-text">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm text-text-muted">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  description: string;
  action?: ReactNode;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description,
  action,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-xl border border-danger/30 bg-danger-soft px-5 py-4",
        className,
      )}
    >
      <h3 className="text-sm font-semibold text-danger">{title}</h3>
      <p className="mt-1 text-sm text-text-muted">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-surface-muted", className)}
      aria-hidden="true"
    />
  );
}

/** Placeholder matching the stat row so the overview does not jump on load. */
export function StatRowSkeleton({ tiles = 4 }: { tiles?: number }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: tiles }).map((_, index) => (
        <div
          key={index}
          className="rounded-xl border border-border bg-surface px-5 py-4"
        >
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-3 h-7 w-32" />
        </div>
      ))}
    </div>
  );
}

export function CardSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <Skeleton className="h-4 w-40" />
      <div className="mt-5 space-y-3">
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} className="h-4 w-full" />
        ))}
      </div>
    </div>
  );
}
