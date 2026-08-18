"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";

import {
  RequiredMark,
  largeControlClassName,
  noticeToneClassName,
  outlineControlButtonClassName,
  type Notice,
} from "@/components/ui/Field";

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
  /** Draws the required marker. Validation itself belongs to the form. */
  required?: boolean;
  /** Display-only transform. Matching and de-duplication still use the raw value. */
  formatValue?: (value: string) => string;
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
  required = false,
  formatValue = (value) => value,
  onChange,
}: TokenInputProps) {
  const [draftValue, setDraftValue] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [notice, setNotice] = useState<Notice | null>(null);
  const blurTimerRef = useRef<number | null>(null);
  const anchorRef = useRef<HTMLDivElement | null>(null);

  const [menuPlacement, setMenuPlacement] = useState<"up" | "down">("down");
  const [menuMaxHeight, setMenuMaxHeight] = useState(288);

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

  useEffect(() => {
  if (!isOpen) {
    return;
  }

  function updateMenuPlacement() {
    const anchor = anchorRef.current;

    if (!anchor) {
      return;
    }

    const rect = anchor.getBoundingClientRect();

    const viewportTop = window.visualViewport?.offsetTop ?? 0;
    const viewportHeight =
      window.visualViewport?.height ?? window.innerHeight;
    const viewportBottom = viewportTop + viewportHeight;

    const gap = 8;
    const preferredHeight = 288;
    const minimumUsefulHeight = 160;

    const spaceBelow = Math.max(
      0,
      viewportBottom - rect.bottom - gap,
    );

    const spaceAbove = Math.max(
      0,
      rect.top - viewportTop - gap,
    );

    const shouldOpenUp =
      spaceBelow < minimumUsefulHeight && spaceAbove > spaceBelow;

    if (shouldOpenUp) {
      setMenuPlacement("up");
      setMenuMaxHeight(
        Math.max(120, Math.min(preferredHeight, spaceAbove)),
      );
    } else {
      setMenuPlacement("down");
      setMenuMaxHeight(
        Math.max(120, Math.min(preferredHeight, spaceBelow)),
      );
    }
  }

  updateMenuPlacement();

  window.addEventListener("resize", updateMenuPlacement);
  window.addEventListener("scroll", updateMenuPlacement, true);

  return () => {
    window.removeEventListener("resize", updateMenuPlacement);
    window.removeEventListener("scroll", updateMenuPlacement, true);
  };
}, [isOpen]);

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

  /**
   * What Enter should add.
   *
   * The highlighted suggestion wins. Failing that, when only listed values are
   * allowed, the top suggestion is taken if what was typed is the start of it:
   * typing "Postgres" showed "postgresql" in the list and then rejected it on
   * Enter, because the raw text was committed instead of the match on screen.
   * A merely-contains match is not enough, or "z" would silently add "azure".
   */
  function resolveEnterValue(): string {
    if (activeIndex >= 0 && matches[activeIndex]) {
      return matches[activeIndex];
    }

    const query = draftValue.trim().toLowerCase();
    const topMatch = matches[0];

    if (!allowCustomValues && query && topMatch) {
      if (matches.length === 1 || topMatch.toLowerCase().startsWith(query)) {
        return topMatch;
      }
    }

    return draftValue;
  }

  function commitDraft(rawValue: string) {
    const { accepted, rejected } = addValues([rawValue]);

    if (rejected.length > 0) {
      setNotice({
        text: `"${rejected[0]}" is not in the list. Pick a suggestion below.`,
        tone: "error",
      });
      return;
    }

    if (accepted.length > 0) {
      setNotice(null);
      setDraftValue("");
      setActiveIndex(-1);
      setIsOpen(false);
    }
  }

  function removeValue(valueToRemove: string) {
    setNotice(null);
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
      setNotice({
        text: "None of that text matched a skill in the list. Try picking skills one at a time.",
        tone: "error",
      });
      return;
    }

    setNotice(
      rejected.length > 0
        ? {
            text: `Added ${accepted.length}. ${rejected.length} not recognised and skipped.`,
            tone: "error",
          }
        : { text: `Added ${accepted.length} skills.`, tone: "success" },
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
      commitDraft(resolveEnterValue());
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
    <div>
      <label htmlFor={id} className="block text-base font-medium text-text">
        {label}
      </label>

      {values.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-2">
          {values.map((value) => (
            <li key={value}>
              <span className="inline-flex items-center gap-2 rounded-full border border-accent/25 bg-accent-soft px-3 py-1.5 text-sm text-accent">
                {formatValue(value)}
                <button
                  type="button"
                  onClick={() => removeValue(value)}
                  className="rounded-full opacity-70 hover:opacity-100"
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

      <div className="relative mt-1.5 flex items-start gap-2">
        {required ? <RequiredMark /> : null}
        <div ref={anchorRef} className="relative min-w-0 flex-1">
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
            className={`${largeControlClassName} pr-10`}
            onChange={(event) => {
              setDraftValue(event.target.value.slice(0, MAX_VALUE_LENGTH));
              setNotice(null);
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

          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
            className="pointer-events-none absolute inset-y-0 right-3 my-auto h-4 w-4 text-text-subtle"
          >
            <path
              d="M4.5 6.25 8 9.75l3.5-3.5"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          {isOpen && matches.length > 0 ? (
            <ul
              id={listId}
              role="listbox"
              aria-label={`${label} suggestions`}
              style={{ maxHeight: menuMaxHeight }}
              className={`absolute left-0 right-0 z-50 overflow-y-auto overscroll-contain rounded-lg border border-border bg-surface py-1 shadow-lg ${
                menuPlacement === "up"
                  ? "bottom-full mb-1"
                  : "top-full mt-1"
              }`}
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
                    {formatValue(suggestion)}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        {values.length > 0 ? (
          <button
            type="button"
            onClick={() => {
              setNotice(null);
              onChange([]);
            }}
            className={outlineControlButtonClassName}
          >
            Clear
            <span className="sr-only"> {label.toLowerCase()}</span>
          </button>
        ) : null}
      </div>

      {notice ? (
        <p role="status" className={`mt-2 ${noticeToneClassName[notice.tone]}`}>
          {notice.text}
        </p>
      ) : null}

      {hint ? (
        <p id={hintId} className="mt-2 text-xs text-text-subtle">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
