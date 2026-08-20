import { render, screen, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CountUp } from "@/components/ui/CountUp";

/**
 * The count cannot be watched in a real browser here, so the two things that
 * decide whether it behaves are pinned instead: it must show the finished
 * figure until motion is both wanted and visible, and it must land exactly
 * on that figure rather than near it.
 */
let intersect: (() => void) | null = null;
let frameCallbacks: FrameRequestCallback[] = [];
let now = 0;

function runFrame(atMs: number) {
  now = atMs;
  const pending = frameCallbacks;
  frameCallbacks = [];
  act(() => {
    pending.forEach((callback) => callback(now));
  });
}

beforeEach(() => {
  intersect = null;
  frameCallbacks = [];
  now = 0;

  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: IntersectionObserverCallback) {
        intersect = () =>
          act(() => {
            callback(
              [{ isIntersecting: true } as IntersectionObserverEntry],
              this as unknown as IntersectionObserver,
            );
          });
      }
      observe() {}
      disconnect() {}
      unobserve() {}
    },
  );

  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    frameCallbacks.push(callback);
    return frameCallbacks.length;
  });
  vi.stubGlobal("cancelAnimationFrame", () => {});
  vi.stubGlobal("performance", { now: () => now });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubMotionPreference(reduced: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockReturnValue({ matches: reduced }) as unknown as typeof matchMedia,
  );
}

describe("CountUp", () => {
  it("counts from zero up to the figure once it is scrolled into view", () => {
    stubMotionPreference(false);
    render(<CountUp value={61} durationMs={1000} format={String} />);

    // Before anything is seen, the real figure stands.
    expect(screen.getByText("61")).toBeTruthy();

    intersect?.();
    runFrame(0);
    expect(screen.getByText("0")).toBeTruthy();

    runFrame(500);
    const midway = Number(screen.getByText(/^\d+$/).textContent);
    expect(midway).toBeGreaterThan(0);
    expect(midway).toBeLessThan(61);

    runFrame(1000);
    expect(screen.getByText("61")).toBeTruthy();
  });

  it("does not start counting in a tab that is already in the background", () => {
    stubMotionPreference(false);
    Object.defineProperty(document, "hidden", { value: true, configurable: true });

    render(<CountUp value={61} durationMs={1000} format={String} />);
    intersect?.();

    // Nothing was scheduled, so the figure cannot be stranded near zero.
    expect(frameCallbacks).toHaveLength(0);
    expect(screen.getByText("61")).toBeTruthy();

    Object.defineProperty(document, "hidden", { value: false, configurable: true });
  });

  it("settles on the figure when the tab goes away mid-count", () => {
    stubMotionPreference(false);
    render(<CountUp value={61} durationMs={1000} format={String} />);

    intersect?.();
    runFrame(0);
    runFrame(200);
    expect(screen.queryByText("61")).toBeNull();

    // Frames stop arriving in a background tab, so the count must not be
    // left stranded part way up.
    Object.defineProperty(document, "hidden", { value: true, configurable: true });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(screen.getByText("61")).toBeTruthy();
    Object.defineProperty(document, "hidden", { value: false, configurable: true });
  });

  it("leaves the figure alone when less motion is asked for", () => {
    stubMotionPreference(true);
    render(<CountUp value={61} durationMs={1000} format={String} />);

    expect(screen.getByText("61")).toBeTruthy();

    // Nothing was scheduled, so nothing can wind it back to zero.
    expect(frameCallbacks).toHaveLength(0);
    expect(intersect).toBeNull();
  });
});
