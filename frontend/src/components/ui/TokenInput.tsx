"use client";

import { useId, useState, type KeyboardEvent } from "react";

import { controlClassName } from "@/components/ui/Field";

interface TokenInputProps {
  id: string;
  label: string;
  hint?: string;
  placeholder?: string;
  values: string[];
  suggestions: string[];
  maxValues?: number;
  onChange: (values: string[]) => void;
}

/**
 * Multi-value entry backed by a native input and datalist. Values are added
 * with Enter or by picking a suggestion, and removed with Backspace or the
 * chip button, so no combobox library is needed.
 */
export function TokenInput({
  id,
  label,
  hint,
  placeholder,
  values,
  suggestions,
  maxValues = 50,
  onChange,
}: TokenInputProps) {
  const [draftValue, setDraftValue] = useState("");
  const listId = useId();
  const hintId = hint ? `${id}-hint` : undefined;

  const availableSuggestions = suggestions
    .filter((suggestion) => !values.includes(suggestion))
    .slice(0, 200);

  function addValue(rawValue: string) {
    const nextValue = rawValue.trim();

    if (!nextValue || values.includes(nextValue) || values.length >= maxValues) {
      setDraftValue("");
      return;
    }

    onChange([...values, nextValue]);
    setDraftValue("");
  }

  function removeValue(valueToRemove: string) {
    onChange(values.filter((value) => value !== valueToRemove));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      addValue(draftValue);
      return;
    }

    if (event.key === "Backspace" && !draftValue && values.length > 0) {
      removeValue(values[values.length - 1]);
    }
  }

  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-text">
        {label}
      </label>

      <input
        id={id}
        list={listId}
        value={draftValue}
        placeholder={placeholder}
        aria-describedby={hintId}
        className={controlClassName}
        onChange={(event) => {
          const nextValue = event.target.value;

          // Picking from the datalist fires change with the full value.
          if (availableSuggestions.includes(nextValue)) {
            addValue(nextValue);
            return;
          }

          setDraftValue(nextValue);
        }}
        onKeyDown={handleKeyDown}
        onBlur={() => addValue(draftValue)}
      />
      <datalist id={listId}>
        {availableSuggestions.map((suggestion) => (
          <option key={suggestion} value={suggestion} />
        ))}
      </datalist>

      {values.length > 0 ? (
        <div className="flex items-center justify-between gap-3 pt-1">
          <p className="text-xs text-text-subtle">
            {values.length} added
          </p>
          <button
            type="button"
            onClick={() => onChange([])}
            className="text-xs font-medium text-text-muted underline underline-offset-2 hover:text-text"
          >
            Clear all
            <span className="sr-only"> {label.toLowerCase()}</span>
          </button>
        </div>
      ) : null}

      {values.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5">
          {values.map((value) => (
            <li key={value}>
              <span className="inline-flex items-center gap-1 rounded-md bg-accent-soft py-0.5 pl-2 pr-1 text-xs font-medium text-accent">
                {value}
                <button
                  type="button"
                  onClick={() => removeValue(value)}
                  className="rounded p-0.5 hover:bg-accent/15"
                >
                  <span className="sr-only">Remove {value}</span>
                  <svg
                    width="10"
                    height="10"
                    viewBox="0 0 10 10"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M1.5 1.5l7 7m0-7l-7 7"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                  </svg>
                </button>
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {hint ? (
        <p id={hintId} className="text-xs text-text-subtle">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
