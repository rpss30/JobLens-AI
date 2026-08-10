"use client";

import {
  useId,
  useMemo,
  useRef,
  useState,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";

import { controlClassName } from "@/components/ui/Field";

const MAX_VISIBLE_SUGGESTIONS = 50;
const MAX_VALUE_LENGTH = 80;

interface TokenInputProps {
  id: string;
  label: string;
  hint?: string;
  placeholder?: string;
  values: string[];
  suggestions: string[];
  maxValues?: number;
  /**
   * When false, only values present in `suggestions` are accepted. Skills use
   * this so a pasted paragraph cannot become one meaningless tag.
   */
  allowCustomValues?: boolean;
  onChange: (values: string[]) => void;
}

/** Splits pasted text on the separators people actually use in skill lists. */
function splitPastedText(text: string): string[] {
  return text
    .split(/[,;\n\r\t|•]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

export function TokenInput({
  id,
  label,
  hint,
  placeholder,
  values,
  suggestions,
  maxValues = 50,
  allowCustomValues = true,
  onChange,
}: TokenInputProps) {
  const [draftValue, setDraftValue] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [notice, setNotice] = useState("");
  const blurTimerRef = useRef<number | null>(null);

  const listId = useId();
  const hintId = hint ? `${id}-hint` : undefined;

  // Duplicate checks are case-insensitive so "docker" and "Docker" cannot both
  // end up in the list.
  const selectedKeys = useMemo(
    () => new Set(values.map((value) => value.toLowerCase())),
    [values],
  );

  const suggestionByKey = useMemo(() => {
    const lookup = new Map<string, string>();

    suggestions.forEach((suggestion) => {
      const key = suggestion.toLowerCase();

      if (!lookup.has(key)) {
        lookup.set(key, suggestion);
      }
    });

    return lookup;
  }, [suggestions]);

  const matches = useMemo(() => {
    const query = draftValue.trim().toLowerCase();
    const available = suggestions.filter(
      (suggestion) => !selectedKeys.has(suggestion.toLowerCase()),
    );

    if (!query) {
      return available.slice(0, MAX_VISIBLE_SUGGESTIONS);
    }

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
  }, [draftValue, suggestions, selectedKeys]);

  const isAtLimit = values.length >= maxValues;

  /** Adds several values at once so one paste cannot drop earlier entries. */
  function addValues(rawValues: string[]) {
    const accepted: string[] = [];
    const rejected: string[] = [];
    const seenKeys = new Set(selectedKeys);

    for (const rawValue of rawValues) {
      const trimmed = rawValue.trim().slice(0, MAX_VALUE_LENGTH);
      const key = trimmed.toLowerCase();

      if (!trimmed || seenKeys.has(key)) {
        continue;
      }

      if (values.length + accepted.length >= maxValues) {
        break;
      }

      const knownSuggestion = suggestionByKey.get(key);

      if (!knownSuggestion && !allowCustomValues) {
        rejected.push(trimmed);
        continue;
      }

      // Prefer the spelling from the dataset so casing stays consistent.
      accepted.push(knownSuggestion ?? trimmed);
      seenKeys.add(key);
    }

    if (accepted.length > 0) {
      onChange([...values, ...accepted]);
    }

    return { accepted, rejected };
  }

  function commitDraft(rawValue: string) {
    const { accepted, rejected } = addValues([rawValue]);

    if (rejected.length > 0) {
      setNotice(`"${rejected[0]}" is not in the list. Pick a suggestion below.`);
      return;
    }

    if (accepted.length > 0) {
      setNotice("");
      setDraftValue("");
      setActiveIndex(-1);
      setIsOpen(false);
    }
  }

  function removeValue(valueToRemove: string) {
    setNotice("");
    onChange(values.filter((value) => value !== valueToRemove));
  }

  function handlePaste(event: ClipboardEvent<HTMLInputElement>) {
    const pastedText = event.clipboardData.getData("text");
    const parts = splitPastedText(pastedText);

    // A single short word behaves like normal typing.
    if (parts.length <= 1 && pastedText.length <= MAX_VALUE_LENGTH) {
      return;
    }

    event.preventDefault();

    const { accepted, rejected } = addValues(parts);

    setDraftValue("");
    setIsOpen(false);
    setActiveIndex(-1);

    if (accepted.length === 0) {
      setNotice(
        "None of that text matched a skill in the list. Try picking skills one at a time.",
      );
      return;
    }

    setNotice(
      rejected.length > 0
        ? `Added ${accepted.length}. ${rejected.length} not recognised and skipped.`
        : `Added ${accepted.length} skills.`,
    );
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
      setActiveIndex((index) => (index <= 0 ? matches.length - 1 : index - 1));
      return;
    }

    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commitDraft(
        activeIndex >= 0 && matches[activeIndex]
          ? matches[activeIndex]
          : draftValue,
      );
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
            setDraftValue(event.target.value.slice(0, MAX_VALUE_LENGTH));
            setNotice("");
            setIsOpen(true);
            setActiveIndex(-1);
          }}
          onPaste={handlePaste}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          onBlur={() => {
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
            className="absolute left-0 right-0 top-full z-20 mt-1 max-h-72 overflow-y-auto rounded-lg border border-border bg-surface py-1 shadow-lg"
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
                    event.preventDefault();

                    if (blurTimerRef.current) {
                      window.clearTimeout(blurTimerRef.current);
                    }
                  }}
                  onClick={() => commitDraft(suggestion)}
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      {notice ? (
        <p role="status" className="text-xs text-text-muted">
          {notice}
        </p>
      ) : null}

      {values.length > 0 ? (
        <>
          <div className="flex items-center justify-between gap-3 pt-1">
            <p className="text-xs text-text-subtle">{values.length} added</p>
            <button
              type="button"
              onClick={() => {
                setNotice("");
                onChange([]);
              }}
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
