import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md";

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-white border-transparent hover:bg-accent-hover disabled:hover:bg-accent",
  secondary:
    "bg-surface text-text border-border-strong hover:bg-surface-muted disabled:hover:bg-surface",
  ghost:
    "bg-transparent text-text-muted border-transparent hover:bg-surface-muted hover:text-text",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
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
        "inline-flex items-center justify-center gap-2 rounded-lg border font-medium transition-colors",
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
