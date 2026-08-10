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
