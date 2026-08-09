import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type BadgeTone = "neutral" | "accent" | "positive" | "warning" | "danger";

/*
 * The palette is monochrome, so meaning is carried by fill weight rather than
 * hue: solid chips read as held or achieved, outlined chips as missing.
 */
const toneStyles: Record<BadgeTone, string> = {
  neutral: "bg-surface-muted text-text-muted border-border",
  accent: "bg-accent-soft text-accent border-transparent",
  positive: "bg-accent text-surface border-transparent",
  warning: "bg-transparent text-text-subtle border-border-strong border-dashed",
  danger: "bg-danger-soft text-danger border-text font-semibold",
};

interface BadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}

export function Badge({ children, tone = "neutral", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        toneStyles[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
