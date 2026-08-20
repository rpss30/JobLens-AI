"use client";

import { useEffect, useRef, useState } from "react";

import { formatCount } from "@/lib/format";

/**
 * A figure that counts up once it has been scrolled into view.
 *
 * The number is the point of the tile it sits in, so it arrives rather than
 * simply being there. It renders its finished value first and only winds
 * back to zero once the browser has confirmed motion is wanted, which keeps
 * the server output honest and leaves the real figure on screen when
 * scripting never runs.
 */
export function CountUp({
  value,
  durationMs = 1200,
  decimals = 0,
  format = formatCount,
}: {
  value: number;
  durationMs?: number;
  /**
   * How far to count in. A tally counts in whole numbers; a percentage
   * rounded to a tenth has to as well, or it lands on a figure a tenth away
   * from the one it settles on.
   */
  decimals?: number;
  /**
   * Defaulted rather than required: a server component cannot hand a
   * function across the boundary, and counting is what this is for.
   */
  format?: (value: number) => string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(value);

  useEffect(() => {
    const node = ref.current;

    if (!node) {
      return;
    }

    // The finished figure is already on screen, so there is nothing to do
    // for anyone who has asked for less motion.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }

    let frame = 0;

    // Frames stop arriving while a tab is in the background, which would
    // otherwise strand the count part way up. Settle on the figure instead:
    // a half finished number is worse than no animation at all.
    const settle = () => {
      if (document.hidden) {
        cancelAnimationFrame(frame);
        setShown(value);
      }
    };

    document.addEventListener("visibilitychange", settle);

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) {
          return;
        }

        observer.disconnect();

        // No frames will arrive if the page is already in the background, so
        // there is nothing to animate towards. Take the figure and be done.
        if (document.hidden) {
          setShown(value);
          return;
        }

        const startedAt = performance.now();

        const step = (now: number) => {
          const progress = Math.min(1, (now - startedAt) / durationMs);
          // Fast away from zero, settling gently onto the figure.
          const eased = 1 - (1 - progress) ** 3;

          setShown(
            decimals > 0
              ? Number((value * eased).toFixed(decimals))
              : Math.round(value * eased),
          );

          if (progress < 1) {
            frame = requestAnimationFrame(step);
          }
        };

        // Wound back inside the callback rather than the effect body, so the
        // rendered figure stands until the browser is ready to animate it.
        setShown(0);
        frame = requestAnimationFrame(step);
      },
      { threshold: 0.5 },
    );

    observer.observe(node);

    return () => {
      document.removeEventListener("visibilitychange", settle);
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [value, durationMs, decimals]);

  return (
    <span ref={ref} className="tabular-nums">
      {format(shown)}
    </span>
  );
}
