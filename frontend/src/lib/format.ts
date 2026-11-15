const numberFormatter = new Intl.NumberFormat("en-CA");

const dateFormatter = new Intl.DateTimeFormat("en-CA", {
  year: "numeric",
  month: "short",
  day: "numeric",
});

export function formatCount(value: number): string {
  return numberFormatter.format(value);
}

export function formatPercent(value: number, fractionDigits = 1): string {
  return `${value.toFixed(fractionDigits)}%`;
}

export function formatDate(value: string): string {
  if (!value) {
    return "";
  }

  const parsedDate = new Date(value);

  return Number.isNaN(parsedDate.getTime())
    ? value
    : dateFormatter.format(parsedDate);
}

/*
 * Skills arrive in mixed casing: extraction preserves the source spelling, but
 * the matching engine normalizes to lowercase. Naive title case turns "aws"
 * into "Aws", so known acronyms and product names are spelled explicitly and
 * everything else falls back to title case.
 */
const SKILL_SPELLINGS: Record<string, string> = {
  ai: "AI",
  api: "API",
  apis: "APIs",
  aws: "AWS",
  "ci/cd": "CI/CD",
  css: "CSS",
  etl: "ETL",
  gcp: "GCP",
  github: "GitHub",
  graphql: "GraphQL",
  html: "HTML",
  javascript: "JavaScript",
  jvm: "JVM",
  llm: "LLM",
  llms: "LLMs",
  ml: "ML",
  mlflow: "MLflow",
  mlops: "MLOps",
  mongodb: "MongoDB",
  mysql: "MySQL",
  nlp: "NLP",
  "node.js": "Node.js",
  nodejs: "Node.js",
  opentelemetry: "OpenTelemetry",
  postgresql: "PostgreSQL",
  pytorch: "PyTorch",
  rest: "REST",
  sql: "SQL",
  sre: "SRE",
  tensorflow: "TensorFlow",
  typescript: "TypeScript",
  ui: "UI",
  ux: "UX",
};

export function formatSkill(skill: string): string {
  const trimmedSkill = skill.trim();

  if (!trimmedSkill) {
    return trimmedSkill;
  }

  const knownSpelling = SKILL_SPELLINGS[trimmedSkill.toLowerCase()];

  if (knownSpelling) {
    return knownSpelling;
  }

  // Anything the source already capitalized is left as the extractor wrote it.
  if (trimmedSkill !== trimmedSkill.toLowerCase()) {
    return trimmedSkill;
  }

  return trimmedSkill
    .split(" ")
    .map((word) => SKILL_SPELLINGS[word] ?? word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function formatDatasetLabel(datasetName: string): string {
  const labels: Record<string, string> = {
    local_sample: "Local sample",
    canada_snapshot: "Canada snapshot",
    early_career_global: "Global early career",
  };

  return labels[datasetName] ?? datasetName;
}

export interface LocationTag {
  /** The place the tag names outright. */
  lead: string;
  /** How many further places the posting lists. */
  extraCount: number;
}

/**
 * Reduces the places a posting names to one tag.
 *
 * A posting open in twelve cities gets one tag rather than twelve: the row of
 * them wrapped over three lines and pushed everything else out of the header.
 *
 * The lead is the place the reader asked for, where they asked for one. A
 * posting that answers a search for Seattle should say so, not name whichever
 * city the board happened to list first.
 */
export function locationTag(
  locations: string[],
  fallback: string,
  selected?: string,
): LocationTag | null {
  const places = (locations.length > 0 ? locations : [fallback]).filter(Boolean);

  if (places.length === 0) {
    return null;
  }

  const asked = selected && places.includes(selected) ? selected : places[0];

  return { lead: asked, extraCount: places.length - 1 };
}
