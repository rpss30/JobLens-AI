"use client";

import { useSyncExternalStore } from "react";

import { getTheme, setTheme, subscribeToTheme, type Theme } from "@/lib/theme";

function MoonIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M16.5 11.75A6.75 6.75 0 0 1 8.25 3.5a6.75 6.75 0 1 0 8.25 8.25Z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="10" cy="10" r="3.4" />
      <path d="M10 2.4v1.7M10 15.9v1.7M17.6 10h-1.7M4.1 10H2.4M15.37 4.63l-1.2 1.2M5.83 14.17l-1.2 1.2M15.37 15.37l-1.2-1.2M5.83 5.83l-1.2-1.2" />
    </svg>
  );
}

/**
 * Light or dark, and a way back to either.
 *
 * Which one is showing is only known once the browser has been asked, so the
 * button renders its shell on the server and fills the icon in afterwards.
 * Anything else would either guess wrong for half of readers or mismatch what
 * the head script already painted.
 */
export function ThemeToggle({ initialTheme }: { initialTheme: Theme | null }) {
  /*
   * The cookie is the answer where there is one. Where there is not, only the
   * browser can say which way the system is set, so the icon arrives a frame
   * later rather than guessing and contradicting the page behind it.
   */
  const theme = useSyncExternalStore(
    subscribeToTheme,
    getTheme,
    () => initialTheme,
  );

  const next = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      className="inline-flex size-10 shrink-0 items-center justify-center rounded-full border border-border bg-surface text-text-muted transition-colors hover:bg-surface-muted hover:text-text"
    >
      {/* Nothing until the browser has answered, so the icon never contradicts
          the theme already on screen. */}
      {theme === "dark" ? <SunIcon /> : theme === "light" ? <MoonIcon /> : null}
    </button>
  );
}
