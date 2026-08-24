import type { ReactNode } from "react";

interface FieldProps {
  label: string;
  htmlFor: string;
  hint?: string;
  children: ReactNode;
}

/** Label, control, and hint wrapper so every form control is labelled. */
export function Field({ label, htmlFor, hint, children }: FieldProps) {
  const hintId = hint ? `${htmlFor}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      <label
        htmlFor={htmlFor}
        className="block text-sm font-medium text-text"
      >
        {label}
      </label>
      {children}
      {hint ? (
        <p id={hintId} className="text-xs text-text-subtle">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export const controlClassName =
  "w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text " +
  "placeholder:text-text-subtle focus:border-accent focus:outline-none " +
  "disabled:cursor-not-allowed disabled:opacity-60";

/**
 * The analyze form draws its controls larger than the rest of the app. Kept
 * separate from controlClassName so the Jobs filters and dataset forms are not
 * resized along with it.
 */
export const largeControlClassName =
  "w-full rounded-lg border border-border bg-surface px-4 py-3 text-[0.9375rem] text-text " +
  "placeholder:text-text-subtle focus:border-accent focus:outline-none " +
  "disabled:cursor-not-allowed disabled:opacity-60";


/**
 * Marks a field the form will not submit without.
 *
 * Absolutely positioned just above the control it belongs to. Sitting in the
 * flow, it added a whole line of empty space between the label and the field.
 */
export function RequiredMark() {
  return (
    <span
      className="absolute bottom-full right-0 mb-1 text-xl leading-none text-required"
      aria-hidden="true"
    >
      *
    </span>
  );
}

/**
 * The outline button that sits beside the analyze form's large controls.
 *
 * Shared as a class rather than a Button variant because Button's own border,
 * height, and text size would have to be overridden, and the class merger here
 * joins strings without resolving Tailwind conflicts.
 */
export const outlineControlButtonClassName =
  "inline-flex shrink-0 items-center justify-center rounded-lg border border-border " +
  "bg-surface px-4 py-3 text-[0.9375rem] text-text transition-colors " +
  "hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-55";

export type NoticeTone = "error" | "success";

export interface Notice {
  text: string;
  tone: NoticeTone;
}

/**
 * Inline feedback beside a control. Errors match the form's validation
 * messages so every "you need to fix this" reads the same; confirmations keep
 * the same size but stay quiet, because colouring them red would cry wolf.
 */
export const noticeToneClassName: Record<NoticeTone, string> = {
  error: "text-xs font-medium text-required",
  success: "text-xs text-text-muted",
};
