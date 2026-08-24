/*
 * Puts the shape back into a job description.
 *
 * Postings arrive as one unbroken block: the paragraph breaks were lost when
 * the posting was fetched, and they are missing from the raw feed too, so
 * there is nothing to recover them from. What survives is the wording — the
 * section headings and list markers are still in the text, just inline.
 *
 * So breaks are added only where the text says a section or a list item
 * begins, never at a guessed interval. A posting whose wording gives no
 * signal is left as the single block it really is, rather than being chopped
 * into paragraphs that were never there.
 */

export type DescriptionBlock =
  | { kind: "heading"; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "bullet"; text: string };

const SECTION_HEADINGS = [
  "About the role",
  "About the team",
  "About us",
  "The opportunity",
  "What you'll do",
  "What you will do",
  "What you'll bring",
  "What you'll need",
  "Responsibilities",
  "Key responsibilities",
  "Requirements",
  "Qualifications",
  "Minimum qualifications",
  "Preferred qualifications",
  "Who you are",
  "What we're looking for",
  "What we offer",
  "Benefits",
  "Perks and benefits",
  "Compensation",
  "Why join us",
  "Why join",
  "Our team",
  "Nice to have",
  "How to apply",
  "Equal opportunity",
  "Salary range",
];

function escapeForRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Longest first, so "About the role" is not matched as "About us". */
const HEADING_PATTERN = new RegExp(
  `(?:(?<=[.!?:])|^)\\s*(${[...SECTION_HEADINGS]
    .sort((first, second) => second.length - first.length)
    .map(escapeForRegExp)
    .join("|")})\\b:?\\s+`,
  "gi",
);

/*
 * Several of these phrases open ordinary sentences: "Our team is a collection
 * of…", "Benefits and total rewards may vary by region". A heading introduces
 * something new, so it is followed by a capital, a number, or a list marker —
 * never by the rest of its own sentence. Checked here rather than in the
 * pattern because the pattern matches case-insensitively, which would let a
 * lowercase word through.
 */
function startsNewBlock(following: string): boolean {
  return !/^[a-z]/.test(following);
}

/*
 * A marker only counts when something list-like follows it. Requiring a
 * capital or a digit keeps a hyphen used as punctuation, as in "a well -
 * known team", from starting a bullet.
 */
const BULLET_PATTERN = /\s[-•]\s+(?=[A-Z0-9])/g;

const LEADING_MARKER = /^[-•]\s+/;

function splitIntoBullets(segment: string): DescriptionBlock[] {
  const trimmed = segment.trim();
  // A segment that opens with a marker is a list item itself, not the prose
  // that introduces one. That happens whenever a heading precedes the list.
  const opensWithMarker = LEADING_MARKER.test(trimmed);

  const pieces = trimmed
    .replace(LEADING_MARKER, "")
    .split(BULLET_PATTERN)
    .map((piece) => piece.trim())
    .filter(Boolean);

  return pieces.map((text, index) => ({
    kind: index === 0 && !opensWithMarker ? "paragraph" : "bullet",
    text,
  }));
}

export function splitJobDescription(description: string): DescriptionBlock[] {
  const text = description.trim();

  if (!text) {
    return [];
  }

  const blocks: DescriptionBlock[] = [];
  let cursor = 0;

  for (const match of text.matchAll(HEADING_PATTERN)) {
    const start = match.index ?? 0;
    const end = start + match[0].length;

    if (!startsNewBlock(text.slice(end, end + 1))) {
      continue;
    }

    if (start > cursor) {
      blocks.push(...splitIntoBullets(text.slice(cursor, start)));
    }

    blocks.push({ kind: "heading", text: match[1] });
    cursor = end;
  }

  if (cursor < text.length) {
    blocks.push(...splitIntoBullets(text.slice(cursor)));
  }

  return blocks.filter((block) => block.text.length > 0);
}

/*
 * A description that kept its own line breaks needs no guessing: the blank
 * lines are the paragraphs and the markers are the list items. A line is only
 * read as a heading when it is short, does not end mid-thought, and has
 * something under it, which is how a board writes one.
 */
const HEADING_MAX_LENGTH = 70;

function blocksFromLineBreaks(text: string): DescriptionBlock[] {
  const lines = text.split("\n").map((line) => line.trim());
  const blocks: DescriptionBlock[] = [];

  for (const [index, line] of lines.entries()) {
    if (!line) {
      continue;
    }

    if (LEADING_MARKER.test(line)) {
      blocks.push({ kind: "bullet", text: line.replace(LEADING_MARKER, "") });
      continue;
    }

    const hasMoreBelow = lines.slice(index + 1).some(Boolean);
    const looksLikeHeading =
      line.length <= HEADING_MAX_LENGTH && !/[.,]$/.test(line) && hasMoreBelow;

    blocks.push({ kind: looksLikeHeading ? "heading" : "paragraph", text: line });
  }

  return blocks;
}

/**
 * The blocks to render for one posting.
 *
 * Prefers the description the board actually wrote. Postings that closed
 * before the dataset was filled in have only the flattened text, and fall
 * back to the structure inferred from their wording.
 */
export function readJobDescription(
  formatted: string,
  flattened: string,
): DescriptionBlock[] {
  if (formatted.trim()) {
    return blocksFromLineBreaks(formatted);
  }

  return splitJobDescription(flattened);
}
