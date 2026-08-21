import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type ButtonVariant = "primary" | "secondary" | "ghost" | "strong";
type ButtonSize = "sm" | "iconOnlyMobile" | "md" | "lg";

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-accent-fill text-on-accent border-transparent hover:bg-accent-fill-hover disabled:hover:bg-accent-fill",
  secondary:
    "bg-surface text-text border-border-strong hover:bg-surface-muted disabled:hover:bg-surface",
  ghost:
    "bg-transparent text-text-muted border-transparent hover:bg-surface-muted hover:text-text",
  /* Solid rather than tinted: for the one action a page is actually for. */
  strong:
    "bg-accent-strong text-on-accent-strong border-transparent hover:bg-accent-strong-hover disabled:hover:bg-accent-strong",
};

/* Weight lives here rather than in the base classes: two font-weight
   utilities on one element resolve by stylesheet order, not class order. */
const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-sm font-medium",
  /* Square and icon-only on a phone, label and all from sm. One key rather
     than md plus overrides: two padding utilities on one element resolve by
     stylesheet order, not class order, so the override would lose. */
  iconOnlyMobile: "h-10 w-10 px-0 text-sm font-medium sm:w-auto sm:px-4",
  md: "h-10 px-4 text-sm font-medium",
  lg: "h-11 px-5 text-lg font-normal",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /**
   * Use "default" when the button is disabled because the action is already
   * done, rather than because it is unavailable. A not-allowed cursor on a
   * completed action reads as an error.
   */
  disabledCursor?: "not-allowed" | "default";
  children: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  disabledCursor = "not-allowed",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg border transition-colors",
        "disabled:opacity-55",
        disabledCursor === "default"
          ? "disabled:cursor-default"
          : "disabled:cursor-not-allowed",
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
