"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { useDatasetParam } from "@/components/layout/ShellSearchParams";
import { withDataset } from "@/lib/datasets";
import { searchDestinations } from "@/lib/navigation";

function SearchIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      aria-hidden="true"
      className="shrink-0"
    >
      <circle cx="9" cy="9" r="5.25" />
      <path d="m13.2 13.2 3.05 3.05" />
    </svg>
  );
}

/**
 * A way to any view without walking the sidebar to it.
 *
 * It searches the app's own views rather than the data in them: the datasets
 * are already searched from the Jobs page, and a box in the chrome that
 * sometimes means one and sometimes the other would be worse than one that
 * always means the same thing.
 */
export function NavSearch() {
  const router = useRouter();
  const datasetName = useDatasetParam();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const listId = useId();

  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const matches = searchDestinations(query);

  useEffect(() => {
    const focusOnShortcut = (event: globalThis.KeyboardEvent) => {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        /*
         * There are two of these in the page, one in the bar and one behind
         * the phone's tools row, and only ever one of them on screen. Without
         * this the shortcut would land on whichever rendered last.
         */
        if (!inputRef.current || inputRef.current.offsetParent === null) {
          return;
        }

        // The browser binds this to its own search on some platforms, and the
        // reader pressing it here means this one.
        event.preventDefault();
        inputRef.current.focus();
        inputRef.current.select();
      }
    };

    const closeFromOutside = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("keydown", focusOnShortcut);
    document.addEventListener("pointerdown", closeFromOutside);

    return () => {
      document.removeEventListener("keydown", focusOnShortcut);
      document.removeEventListener("pointerdown", closeFromOutside);
    };
  }, []);

  function go(index: number) {
    const destination = matches[index];

    if (!destination) {
      return;
    }

    setQuery("");
    setIsOpen(false);
    inputRef.current?.blur();
    router.push(withDataset(destination.href, datasetName));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      setIsOpen(false);
      inputRef.current?.blur();
      return;
    }

    if (matches.length === 0) {
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % matches.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((index) => (index - 1 + matches.length) % matches.length);
    } else if (event.key === "Enter") {
      event.preventDefault();
      go(activeIndex);
    }
  }

  const isListOpen = isOpen && query.trim().length > 0;
  // A shorter list can leave the highlight past its end, so it is clamped on
  // the way out rather than reset by an effect on the way in.
  const highlighted = Math.min(activeIndex, Math.max(0, matches.length - 1));

  return (
    <div ref={containerRef} className="relative min-w-0 flex-1 sm:max-w-md">
      <div className="flex h-11 items-center gap-2.5 rounded-xl border border-border bg-surface px-3.5 text-text-muted focus-within:border-accent">
        <SearchIcon />
        <input
          ref={inputRef}
          type="search"
          role="combobox"
          aria-expanded={isListOpen}
          aria-controls={listId}
          aria-autocomplete="list"
          value={query}
          placeholder="Search"
          onChange={(event) => {
            setQuery(event.target.value);
            setActiveIndex(0);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          className="min-w-0 flex-1 bg-transparent text-sm text-text outline-none placeholder:text-text-subtle [&::-webkit-search-cancel-button]:hidden"
        />
        {/* Decorative: the shortcut is bound on the document, and the badge
            only says so. */}
        <kbd
          aria-hidden="true"
          className="hidden shrink-0 rounded-md bg-surface-muted px-1.5 py-0.5 text-[0.6875rem] font-medium text-text-subtle sm:block"
        >
          &#8984; K
        </kbd>
      </div>

      {isListOpen ? (
        <div className="absolute left-0 right-0 z-40 mt-2 overflow-hidden rounded-xl border border-border bg-surface py-1.5 shadow-[0_12px_28px_rgba(16,21,31,0.14)]">
          {matches.length === 0 ? (
            <p className="px-4 py-2.5 text-sm text-text-muted">
              Nothing here matches &ldquo;{query.trim()}&rdquo;.
            </p>
          ) : (
            <ul id={listId} role="listbox">
              {matches.map((destination, index) => (
                <li key={destination.href}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === highlighted}
                    onPointerEnter={() => setActiveIndex(index)}
                    onClick={() => go(index)}
                    className={`flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                      index === highlighted
                        ? "bg-accent-soft text-text"
                        : "text-text hover:bg-surface-muted"
                    }`}
                  >
                    <destination.Icon className="shrink-0 text-text-muted" />
                    <span className="min-w-0 flex-1 truncate">
                      {destination.label}
                    </span>
                    {destination.section ? (
                      <span className="shrink-0 text-xs text-text-subtle">
                        {destination.section}
                      </span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
