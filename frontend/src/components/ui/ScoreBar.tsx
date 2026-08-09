import { cn } from "@/lib/cn";
import { formatPercent } from "@/lib/format";

interface ScoreBarProps {
  label: string;
  value: number;
  caption?: string;
  tone?: "accent" | "positive" | "warning";
  className?: string;
}

const toneStyles = {
  accent: "bg-accent",
  positive: "bg-text",
  warning: "bg-border-strong",
};

export function ScoreBar({
  label,
  value,
  caption,
  tone = "accent",
  className,
}: ScoreBarProps) {
  const boundedValue = Math.max(0, Math.min(100, value));

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="truncate text-sm font-medium text-text">{label}</span>
        <span className="shrink-0 text-sm tabular-nums text-text-muted">
          {formatPercent(value)}
        </span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-surface-muted"
        role="meter"
        aria-valuenow={Math.round(boundedValue)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} score`}
      >
        <div
          className={cn("h-full rounded-full", toneStyles[tone])}
          style={{ width: `${boundedValue}%` }}
        />
      </div>
      {caption ? <p className="text-xs text-text-subtle">{caption}</p> : null}
    </div>
  );
}
