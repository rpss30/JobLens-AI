"""Audit real job descriptions for possible missing skill keywords.

This script does not automatically modify src/config/skills.py.

It finds candidate skill terms from skill-related language in real job
descriptions, removes terms already covered by TECH_SKILLS, and exports a
ranked report for manual review.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.config.skills import TECH_SKILLS


PROCESSED_INPUT_PATH = ROOT_DIR / "data" / "processed" / "processed_jobs.csv"
REPORT_OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "skill_candidate_audit.csv"


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "etc",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "using",
    "we",
    "with",
    "you",
    "your",
}


GENERIC_NON_SKILL_TERMS = {
    "ability",
    "analytics",
    "backend",
    "business",
    "candidate",
    "cloud",
    "collaborate",
    "communication",
    "company",
    "complex",
    "customer",
    "data",
    "deliver",
    "delivery",
    "design",
    "develop",
    "development",
    "engineering",
    "enterprise",
    "environment",
    "experience",
    "financial",
    "high",
    "including",
    "insights",
    "junior",
    "knowledge",
    "lead",
    "management",
    "models",
    "organization",
    "platform",
    "product",
    "projects",
    "requirements",
    "role",
    "science",
    "service",
    "services",
    "software",
    "solutions",
    "strong",
    "support",
    "system",
    "systems",
    "team",
    "technical",
    "technologies",
    "technology",
    "tools",
    "work",
    "working",
    "years",
    "relational",
    "non-relational",
    "database",
    "databases",
}


SKILL_CONTEXT_PATTERNS = [
    r"(?:experience|experienced)\s+(?:with|in|using)\s+(.{1,180})",
    r"(?:knowledge|understanding)\s+of\s+(.{1,180})",
    r"(?:proficient|proficiency)\s+(?:with|in)\s+(.{1,180})",
    r"(?:familiarity|familiar)\s+with\s+(.{1,180})",
    r"(?:skills|expertise)\s+(?:with|in)\s+(.{1,180})",
    r"(?:tools|technologies|tech stack)\s+(?:such as|including|include|like)\s+(.{1,180})",
    r"(?:build|building|built|develop|developing|developed)\s+(?:with|using)\s+(.{1,180})",
]


CHUNK_SPLIT_PATTERN = re.compile(
    r",|;|/|\||\band\b|\bor\b|\bplus\b|\bincluding\b|\bsuch as\b",
    flags=re.IGNORECASE,
)


def parse_extracted_skills(value: object) -> list[str]:
    """Parse extracted_skills from the processed CSV into a list."""
    if isinstance(value, list):
        return [str(skill).lower().strip() for skill in value]

    if pd.isna(value):
        return []

    text = str(value).strip()

    if not text:
        return []

    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError):
        return []

    if not isinstance(parsed, list):
        return []

    return [str(skill).lower().strip() for skill in parsed]


def clean_text(text: str) -> str:
    """Normalize text while preserving common technical characters."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9+#./,\s;|-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def truncate_context(context: str) -> str:
    """Trim context at natural sentence/list boundaries."""
    context = re.split(r"\.|\n|\r|\)|\(", context, maxsplit=1)[0]
    return context.strip()


def clean_candidate_term(term: str) -> str:
    """Clean one candidate skill term."""
    term = term.lower().strip()
    term = re.sub(r"[^a-z0-9+#.\s-]", " ", term)
    term = re.sub(r"\s+", " ", term)
    term = term.strip(" .,-")

    words = [
        word
        for word in term.split()
        if word not in GENERIC_NON_SKILL_TERMS and word not in STOPWORDS
    ]

    return " ".join(words).strip()


def is_valid_candidate(term: str) -> bool:
    """Return True if a candidate looks specific enough to review."""
    if not term:
        return False

    if len(term) < 2:
        return False

    if term in STOPWORDS:
        return False

    if term in GENERIC_NON_SKILL_TERMS:
        return False

    if term.isdigit():
        return False

    words = term.split()

    if any(word in STOPWORDS for word in words):
        return False

    if all(word in GENERIC_NON_SKILL_TERMS for word in words):
        return False

    if len(words) > 4:
        return False

    return True


def extract_candidate_terms(description: str) -> set[str]:
    """Extract candidate skill terms from skill-context phrases."""
    cleaned_description = clean_text(description)
    candidates: set[str] = set()

    for pattern in SKILL_CONTEXT_PATTERNS:
        matches = re.findall(pattern, cleaned_description, flags=re.IGNORECASE)

        for match in matches:
            context = truncate_context(match)

            for raw_term in CHUNK_SPLIT_PATTERN.split(context):
                term = clean_candidate_term(raw_term)

                if is_valid_candidate(term):
                    candidates.add(term)

    return candidates


def build_skill_candidate_report(df: pd.DataFrame) -> pd.DataFrame:
    """Build a ranked report of candidate missing skill terms."""
    approved_skills = {skill.lower().strip() for skill in TECH_SKILLS}

    total_mentions: Counter[str] = Counter()
    empty_skill_row_mentions: Counter[str] = Counter()
    unique_job_mentions: defaultdict[str, set[str]] = defaultdict(set)

    for row_index, row in df.iterrows():
        description = str(row.get("description", ""))
        extracted_skills = parse_extracted_skills(row.get("extracted_skills"))
        candidates = extract_candidate_terms(description)

        for candidate in candidates:
            if candidate in approved_skills:
                continue

            total_mentions[candidate] += 1
            unique_job_mentions[candidate].add(str(row.get("job_id", row_index)))

            if not extracted_skills:
                empty_skill_row_mentions[candidate] += 1

    rows = []

    for candidate, mention_count in total_mentions.items():
        unique_jobs = len(unique_job_mentions[candidate])

        if unique_jobs < 2:
            continue

        rows.append(
            {
                "candidate_term": candidate,
                "total_mentions": mention_count,
                "unique_job_postings": unique_jobs,
                "mentions_in_empty_skill_rows": empty_skill_row_mentions[candidate],
            }
        )

    report_df = pd.DataFrame(rows)

    if report_df.empty:
        return pd.DataFrame(
            columns=[
                "candidate_term",
                "total_mentions",
                "unique_job_postings",
                "mentions_in_empty_skill_rows",
            ]
        )

    return report_df.sort_values(
        by=[
            "mentions_in_empty_skill_rows",
            "unique_job_postings",
            "total_mentions",
        ],
        ascending=False,
    )


def main() -> None:
    """Run the skill candidate audit."""
    if not PROCESSED_INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {PROCESSED_INPUT_PATH}. "
            "Run the job processing pipeline first."
        )

    df = pd.read_csv(PROCESSED_INPUT_PATH)
    report_df = build_skill_candidate_report(df)

    REPORT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(REPORT_OUTPUT_PATH, index=False)

    print(f"Saved skill candidate audit to {REPORT_OUTPUT_PATH}")

    if report_df.empty:
        print("No repeated candidate terms found.")
        return

    print("\nTop candidate terms:")
    print(report_df.head(50).to_string(index=False))


if __name__ == "__main__":
    main()
