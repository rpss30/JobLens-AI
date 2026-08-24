/*
 * Icons for role categories. Matched on keywords rather than exact names,
 * because categories come from whatever dataset is loaded and an unknown one
 * should still get something better than a blank tile.
 */

function Glyph({ children }: { children: React.ReactNode }) {
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
    >
      {children}
    </svg>
  );
}

const ICONS: { match: string[]; icon: React.ReactNode }[] = [
  {
    match: ["software", "engineering", "developer", "backend", "frontend"],
    icon: (
      <Glyph>
        <path d="M7 6.5 3.5 10 7 13.5M13 6.5 16.5 10 13 13.5M11.5 4.5l-3 11" />
      </Glyph>
    ),
  },
  {
    match: ["ai", "ml", "machine", "learning"],
    icon: (
      <Glyph>
        <path d="M10 4.2a2.4 2.4 0 0 0-4.3 1.4v.2A2.3 2.3 0 0 0 4.4 8a2.3 2.3 0 0 0 .6 4.4 2.4 2.4 0 0 0 5 1.3z" />
        <path d="M10 4.2a2.4 2.4 0 0 1 4.3 1.4v.2A2.3 2.3 0 0 1 15.6 8a2.3 2.3 0 0 1-.6 4.4 2.4 2.4 0 0 1-5 1.3z" />
      </Glyph>
    ),
  },
  {
    match: ["cloud", "aws", "azure", "devops", "platform", "infrastructure"],
    icon: (
      <Glyph>
        <path d="M6 15.5a3.5 3.5 0 0 1-.3-7A4.5 4.5 0 0 1 14.3 8h.2a3.75 3.75 0 0 1 0 7.5z" />
      </Glyph>
    ),
  },
  {
    match: ["data science", "science", "research"],
    icon: (
      <Glyph>
        <path d="M4 16.5v-5M8 16.5v-9M12 16.5v-6M16 16.5V4.5" />
      </Glyph>
    ),
  },
  {
    match: ["data engineering", "engineering", "pipeline", "warehouse"],
    icon: (
      <Glyph>
        <ellipse cx="10" cy="5.5" rx="5.5" ry="2.3" />
        <path d="M4.5 5.5v4c0 1.3 2.5 2.3 5.5 2.3s5.5-1 5.5-2.3v-4" />
        <path d="M4.5 9.5v4c0 1.3 2.5 2.3 5.5 2.3s5.5-1 5.5-2.3v-4" />
      </Glyph>
    ),
  },
  {
    match: ["analytics", "analyst", "business", "reporting"],
    icon: (
      <Glyph>
        <path d="M10 3.5a6.5 6.5 0 1 0 6.5 6.5H10z" />
        <path d="M12.5 3.9A6.5 6.5 0 0 1 16.1 7.5H12.5z" />
      </Glyph>
    ),
  },
];

const FALLBACK = (
  <Glyph>
    <rect x="3.5" y="3.5" width="13" height="13" rx="3" />
    <path d="M7 10h6" />
  </Glyph>
);

export function CategoryIcon({ category }: { category: string }) {
  const name = category.toLowerCase();
  const match = ICONS.find((entry) =>
    entry.match.some((keyword) => name.includes(keyword)),
  );

  return match ? match.icon : FALLBACK;
}
