"use client";

import { useState } from "react";

/*
 * An employer's mark, fetched from a public favicon service by domain.
 *
 * The domain is a guess for most employers: postings are usually served from
 * an applicant tracking host rather than the company's own site. So the logo
 * is treated as decoration that may not arrive — the request is made without
 * a referrer, and anything that fails to load falls back to a monogram, which
 * is what a company outside the service's index gets too.
 */

const LOGO_SIZE = 128;

/** Deterministic tint, so one company always reads the same colour. */
function tintFor(name: string): number {
  let hash = 0;

  for (const character of name) {
    hash = (hash * 31 + character.charCodeAt(0)) % 360;
  }

  return hash;
}

/** Card tiles and the row beside a table cell want different weights. */
const SIZES = {
  md: { box: "h-10 w-10 rounded-xl text-base", pad: "p-1.5", pixels: 40 },
  /* Beside a posting title, which is held to two lines on a phone and runs
     free from sm. One key rather than md plus overrides: two height
     utilities on one element resolve by stylesheet order, not class order. */
  title: {
    box: "h-12 w-12 rounded-2xl text-lg sm:h-10 sm:w-10 sm:rounded-xl sm:text-base",
    pad: "p-2 sm:p-1.5",
    pixels: 48,
  },
  sm: { box: "h-6 w-6 rounded-md text-[0.6875rem]", pad: "p-0.5", pixels: 24 },
} as const;

export function CompanyLogo({
  name,
  domain,
  size = "md",
}: {
  name: string;
  domain: string;
  size?: keyof typeof SIZES;
}) {
  const [failed, setFailed] = useState(false);
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  const { box, pad, pixels } = SIZES[size];

  if (!domain || failed) {
    const tint = tintFor(name);

    return (
      <span
        aria-hidden="true"
        className={`inline-flex shrink-0 items-center justify-center font-semibold ${box}`}
        style={{
          backgroundColor: `hsl(${tint} 42% 92%)`,
          color: `hsl(${tint} 45% 32%)`,
        }}
      >
        {initial}
      </span>
    );
  }

  return (
    // A third-party favicon, not an asset this app builds or can optimise.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(
        domain,
      )}&sz=${LOGO_SIZE}`}
      alt=""
      width={pixels}
      height={pixels}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className={`shrink-0 border border-border bg-surface object-contain ${box} ${pad}`}
    />
  );
}
