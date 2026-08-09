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

/**
 * Skills arrive from the API in mixed casing because extraction preserves the
 * source spelling. Title-case only the all-lowercase ones so acronyms such as
 * AWS and SQL keep their shape.
 */
export function formatSkill(skill: string): string {
  const trimmedSkill = skill.trim();

  if (!trimmedSkill || trimmedSkill !== trimmedSkill.toLowerCase()) {
    return trimmedSkill;
  }

  return trimmedSkill
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

/** Split the API's comma-joined preview strings back into chips. */
export function parseSkillPreview(preview: string): string[] {
  if (!preview || preview === "None") {
    return [];
  }

  return preview
    .split(",")
    .map((skill) => skill.trim())
    .filter(Boolean);
}

export function formatDatasetLabel(datasetName: string): string {
  const labels: Record<string, string> = {
    local_sample: "Local sample",
    canada_snapshot: "Canada snapshot",
  };

  return labels[datasetName] ?? datasetName;
}
