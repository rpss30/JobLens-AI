"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import {
  RequiredMark,
  controlClassName,
  largeControlClassName,
} from "@/components/ui/Field";

/*
 * A select whose list can be themed.
 *
 * A native select draws its popup through the operating system and no CSS
 * reaches inside it, so the list arrives in the platform's colours however
 * the control is styled. This stands in for one: it flips above the button
 * when there is no room below, sizes itself to the viewport, and follows the
 * keyboard behaviour of the control it replaces.
 */

export function SingleSelectCombobox({
  id,
  label,
  value,
  placeholder,
  options,
  onChange,
  name,
  size = "large",
  required = false,
  leading,
}: {
  id: string;
  /** Rendered above the control. Omit where a Field already labels it. */
  label?: string;
  value: string;
  placeholder: string;
  options: {
    value: string;
    label: string;
  }[];
  onChange: (value: string) => void;
  /** Set to carry the value in a plain GET form. */
  name?: string;
  size?: "large" | "compact";
  required?: boolean;
  /** Drawn inside the control, before the chosen value. */
  leading?: ReactNode;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [menuPlacement, setMenuPlacement] = useState<"up" | "down">("down");
  const [menuMaxHeight, setMenuMaxHeight] = useState(288);

  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const listId = useId();

  function openMenu() {
    const currentIndex = options.findIndex((option) => option.value === value);

    setActiveIndex(currentIndex >= 0 ? currentIndex : 0);
    setIsOpen(true);
  }

  function closeMenu() {
    setIsOpen(false);
    setActiveIndex(-1);
  }

  function selectOption(option: { value: string; label: string }) {
    onChange(option.value);
    closeMenu();

    requestAnimationFrame(() => {
      buttonRef.current?.focus();
    });
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();

      if (!isOpen) {
        openMenu();
        return;
      }

      setActiveIndex((index) => (index >= options.length - 1 ? 0 : index + 1));
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();

      if (!isOpen) {
        openMenu();
        return;
      }

      setActiveIndex((index) => (index <= 0 ? options.length - 1 : index - 1));
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();

      if (!isOpen) {
        openMenu();
        return;
      }

      if (activeIndex >= 0 && options[activeIndex]) {
        selectOption(options[activeIndex]);
      }

      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu();
    }
  }

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function updateMenuPlacement() {
      const button = buttonRef.current;

      if (!button) {
        return;
      }

      const rect = button.getBoundingClientRect();

      const viewportTop = window.visualViewport?.offsetTop ?? 0;
      const viewportHeight =
        window.visualViewport?.height ?? window.innerHeight;
      const viewportBottom = viewportTop + viewportHeight;

      const gap = 8;
      const preferredHeight = 288;
      const minimumUsefulHeight = 160;

      const spaceBelow = Math.max(0, viewportBottom - rect.bottom - gap);

      const spaceAbove = Math.max(0, rect.top - viewportTop - gap);

      const shouldOpenUp =
        spaceBelow < minimumUsefulHeight && spaceAbove > spaceBelow;

      const availableSpace = shouldOpenUp ? spaceAbove : spaceBelow;

      setMenuPlacement(shouldOpenUp ? "up" : "down");
      setMenuMaxHeight(Math.max(96, Math.min(preferredHeight, availableSpace)));
    }

    updateMenuPlacement();

    window.addEventListener("resize", updateMenuPlacement);
    window.addEventListener("scroll", updateMenuPlacement, true);

    return () => {
      window.removeEventListener("resize", updateMenuPlacement);
      window.removeEventListener("scroll", updateMenuPlacement, true);
    };
  }, [isOpen]);

  return (
    <div className={label ? "space-y-3" : undefined}>
      {label ? (
        <label htmlFor={id} className="block text-base font-medium text-text">
          {label}
        </label>
      ) : null}

      {name ? <input type="hidden" name={name} value={value} /> : null}

      <div
        className="relative"
        onBlur={(event) => {
          if (
            !event.currentTarget.contains(event.relatedTarget as Node | null)
          ) {
            closeMenu();
          }
        }}
      >
        {required ? <RequiredMark /> : null}

        <button
          ref={buttonRef}
          id={id}
          type="button"
          role="combobox"
          aria-expanded={isOpen}
          aria-controls={listId}
          aria-haspopup="listbox"
          className={`${
            size === "large" ? largeControlClassName : controlClassName
          } flex w-full items-center justify-between pr-10 text-left ${
            value ? "text-text" : "text-text-subtle"
          }`}
          onClick={() => {
            if (isOpen) {
              closeMenu();
            } else {
              openMenu();
            }
          }}
          onKeyDown={handleKeyDown}
        >
          <span className="flex min-w-0 items-center gap-2">
            {leading ? (
              <span className="shrink-0 text-text-muted">{leading}</span>
            ) : null}
            <span className="truncate">
              {options.find((option) => option.value === value)?.label ||
                placeholder}
            </span>
          </span>
        </button>

        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
          className={`pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-subtle transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        >
          <path
            d="M4.5 6.25 8 9.75l3.5-3.5"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        {isOpen ? (
          <ul
            id={listId}
            role="listbox"
            aria-label={label ? `${label} options` : undefined}
            style={{ maxHeight: menuMaxHeight }}
            className={`absolute left-0 right-0 z-50 overflow-y-auto overscroll-contain rounded-lg border border-border bg-surface py-1 shadow-lg ${
              menuPlacement === "up" ? "bottom-full mb-1" : "top-full mt-1"
            }`}
          >
            {options.map((option, index) => (
              <li key={option.value}>
                <button
                  type="button"
                  role="option"
                  aria-selected={option.value === value}
                  className={`block w-full px-3 py-2 text-left text-sm ${
                    index === activeIndex
                      ? "bg-accent-soft text-accent"
                      : "text-text hover:bg-surface-muted"
                  }`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => selectOption(option)}
                >
                  {option.label}
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
