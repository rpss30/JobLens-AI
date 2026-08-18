/*
 * Hand-drawn icons rather than an icon package. The set needed here is small
 * and fixed, and the frontend deliberately carries no component dependencies.
 *
 * Every glyph inherits colour from its parent and is marked aria-hidden: the
 * nav label beside it is what gets announced.
 */

interface IconProps {
  className?: string;
}

function Glyph({
  className,
  children,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      {children}
    </svg>
  );
}

export function OverviewIcon({ className }: IconProps) {
  return (
    <Glyph className={className}>
      <rect x="2.75" y="3.25" width="14.5" height="13.5" rx="2.25" />
      <path d="M8.25 3.25v13.5M8.25 10h9" />
    </Glyph>
  );
}

export function AnalyzeIcon({ className }: IconProps) {
  return (
    <Glyph className={className}>
      <path d="M2.75 6.5a2 2 0 0 1 2-2h2.9l1.6 2h6a2 2 0 0 1 2 2v5.25a2 2 0 0 1-2 2H4.75a2 2 0 0 1-2-2z" />
      <path d="M2.75 9.25h14.5" />
    </Glyph>
  );
}

export function JobsIcon({ className }: IconProps) {
  return (
    <Glyph className={className}>
      <rect x="2.75" y="6.25" width="14.5" height="10.5" rx="2" />
      <path d="M7.25 6.25V5a1.75 1.75 0 0 1 1.75-1.75h2A1.75 1.75 0 0 1 12.75 5v1.25" />
      <path d="M2.75 10.75h14.5" />
    </Glyph>
  );
}

export function SkillsIcon({ className }: IconProps) {
  return (
    <Glyph className={className}>
      <path d="M3.75 16.25v-4.5M8.25 16.25v-8M12.75 16.25v-5.5M17.25 16.25V4.75" />
    </Glyph>
  );
}

export function HistoryIcon({ className }: IconProps) {
  return (
    <Glyph className={className}>
      <path d="M5.75 3.25h8.5M5.75 16.75h8.5" />
      <path d="M6.75 3.25v3.1c0 1.4 2 2.3 3.25 3.65 1.25-1.35 3.25-2.25 3.25-3.65V3.25" />
      <path d="M6.75 16.75v-3.1c0-1.4 2-2.3 3.25-3.65 1.25 1.35 3.25 2.25 3.25 3.65v3.1" />
    </Glyph>
  );
}

export function DatasetsIcon({ className }: IconProps) {
  return (
    <Glyph className={className}>
      <ellipse cx="10" cy="5.25" rx="6.25" ry="2.5" />
      <path d="M3.75 5.25v4.5c0 1.38 2.8 2.5 6.25 2.5s6.25-1.12 6.25-2.5v-4.5" />
      <path d="M3.75 9.75v4.5c0 1.38 2.8 2.5 6.25 2.5s6.25-1.12 6.25-2.5v-4.5" />
    </Glyph>
  );
}

export function ChevronIcon({ className }: IconProps) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M4.5 6.25 8 9.75l3.5-3.5" />
    </svg>
  );
}

export function MenuIcon({ className }: IconProps) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M3 5.5h14M3 10h14M3 14.5h14" />
    </svg>
  );
}

export function AvatarIcon({ className }: IconProps) {
  return (
    <svg
      width="34"
      height="34"
      viewBox="0 0 34 34"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <circle cx="17" cy="17" r="12.75" />
      <circle cx="17" cy="13.75" r="4" />
      <path d="M8.4 27.2a9.2 9.2 0 0 1 17.2 0" />
    </svg>
  );
}

/**
 * The wordmark's lens mark: an outlined tile holding a filled lens with a
 * highlight arc, and a magnifier handle off its lower right. The tile and
 * lens take the current text colour so the mark inverts with the theme; the
 * highlight is knocked out in the surface colour.
 */
export function LogoMark({ className }: IconProps) {
  return (
    <svg
      width="40"
      height="40"
      viewBox="0 0 40 40"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      aria-hidden="true"
      className={className}
    >
      <rect
        x="3.1"
        y="3.1"
        width="33.8"
        height="33.8"
        rx="8.6"
        strokeWidth="3.2"
      />
      <circle cx="19.3" cy="17.3" r="9.15" fill="currentColor" stroke="none" />
      <path
        d="M19.3 11.5A5.8 5.8 0 0 0 13.5 17.3"
        stroke="var(--color-surface)"
        strokeWidth="1.9"
      />
      <path d="M27.1 25.1 30.6 28.6" strokeWidth="3.2" />
    </svg>
  );
}
