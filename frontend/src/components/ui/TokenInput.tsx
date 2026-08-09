"use client";

import { useId, useMemo, useRef, useState, type KeyboardEvent } from "react";

import { controlClassName } from "@/components/ui/Field";

const MAX_VISIBLE_SUGGESTIONS = 8;

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
 * Multi-value entry with a styled suggestion list.
 *
 * A native <datalist> was used first, but browsers render it as an unstyled
 * popup that ignores the design system and can appear detached from the field,
 * so this implements the combobox pattern directly: the list is owned by the
 * component, sits directly under the input, and is driven by arrow keys,
 * Enter, and Escape.
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
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const blurTimerRef = useRef<number | null>(null);

  const listId = useId();
  const hintId = hint ? `${id}-hint` : undefined;

  const matches = useMemo(() => {
    const query = draftValue.trim().toLowerCase();
    const available = suggestions.filter(
      (suggestion) => !values.includes(suggestion),
    );

    if (!query) {
      return available.slice(0, MAX_VISIBLE_SUGGESTIONS);
    }

    // Prefix matches first, since they are what the typist is most likely after.
    const prefixMatches = available.filter((suggestion) =>
      suggestion.toLowerCase().startsWith(query),
    );
    const containsMatches = available.filter(
      (suggestion) =>
        !suggestion.toLowerCase().startsWith(query) &&
        suggestion.toLowerCase().includes(query),
    );

    return [...prefixMatches, ...containsMatches].slice(
      0,
      MAX_VISIBLE_SUGGESTIONS,
    );
  }, [draftValue, suggestions, values]);

  const isAtLimit = values.length >= maxValues;

  function addValue(rawValue: string) {
    const nextValue = rawValue.trim();

    setDraftValue("");
    setActiveIndex(-1);
    setIsOpen(false);

    if (!nextValue || values.includes(nextValue) || isAtLimit) {
      return;
    }

    onChange([...values, nextValue]);
  }

  function removeValue(valueToRemove: string) {
    onChange(values.filter((value) => value !== valueToRemove));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIsOpen(true);
      setActiveIndex((index) => (index + 1) % Math.max(matches.length, 1));
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) =>
        index <= 0 ? matches.length - 1 : index - 1,
      );
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      addValue(
        activeIndex >= 0 && matches[activeIndex] ? matches[activeIndex] : draftValue,
      );
      return;
    }

    if (event.key === "," ) {
      event.preventDefault();
      addValue(draftValue);
      return;
    }

    if (event.key === "Escape") {
      setIsOpen(false);
      setActiveIndex(-1);
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

      <div className="relative">
        <input
          id={id}
          type="text"
          role="combobox"
          autoComplete="off"
          aria-expanded={isOpen && matches.length > 0}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={
            activeIndex >= 0 ? `${listId}-option-${activeIndex}` : undefined
          }
          aria-describedby={hintId}
          value={draftValue}
          placeholder={isAtLimit ? `Limit of ${maxValues} reached` : placeholder}
          disabled={isAtLimit}
          className={controlClassName}
          onChange={(event) => {
            setDraftValue(event.target.value);
            setIsOpen(true);
            setActiveIndex(-1);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            // Delay so a click on an option lands before the list closes.
            blurTimerRef.current = window.setTimeout(() => {
              setIsOpen(false);
              setActiveIndex(-1);
            }, 120);
          }}
        />

        {isOpen && matches.length > 0 ? (
          <ul
            id={listId}
            role="listbox"
            aria-label={`${label} suggestions`}
            className="absolute left-0 right-0 top-full z-20 mt-1 max-h-64 overflow-y-auto rounded-lg border border-border bg-surface py-1 shadow-lg"
          >
            {matches.map((suggestion, index) => (
              <li key={suggestion}>
                <button
                  type="button"
                  id={`${listId}-option-${index}`}
                  role="option"
                  aria-selected={index === activeIndex}
                  className={`block w-full px-3 py-2 text-left text-sm ${
                    index === activeIndex
                      ? "bg-accent-soft text-accent"
                      : "text-text hover:bg-surface-muted"
                  }`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onMouseDown={(event) => {
                    // Prevent the input blurring before the click registers.
                    event.preventDefault();

                    if (blurTimerRef.current) {
                      window.clearTimeout(blurTimerRef.current);
                    }
                  }}
                  onClick={() => addValue(suggestion)}
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      {values.length > 0 ? (
        <>
          <div className="flex items-center justify-between gap-3 pt-1">
            <p className="text-xs text-text-subtle">{values.length} added</p>
            <button
              type="button"
              onClick={() => onChange([])}
              className="text-xs font-medium text-text-muted underline underline-offset-2 hover:text-text"
            >
              Clear all
              <span className="sr-only"> {label.toLowerCase()}</span>
            </button>
          </div>

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
        </>
      ) : null}

      {hint ? (
        <p id={hintId} className="text-xs text-text-subtle">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
