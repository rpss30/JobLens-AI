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

export function CompanyLogo({
  name,
  domain,
}: {
  name: string;
  domain: string;
}) {
  const [failed, setFailed] = useState(false);
  const initial = name.trim().charAt(0).toUpperCase() || "?";

  if (!domain || failed) {
    const tint = tintFor(name);

    return (
      <span
        aria-hidden="true"
        className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-base font-semibold"
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
      width={40}
      height={40}
      loading="lazy"
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => setFailed(true)}
      className="h-10 w-10 shrink-0 rounded-xl border border-border bg-surface object-contain p-1.5"
    />
  );
}
