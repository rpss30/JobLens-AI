"""Helpers for cleaning and validating AI-extracted skill names."""

from __future__ import annotations

import re


_SEPARATOR_PATTERN = re.compile(r"[/|;]+")

GENERIC_SKILL_TERMS = {
    "ai",
    "systems",
    "platform",
    "business",
    "customer",
    "work",
    "experience",
    "leadership",
    "collaboration",
    "problem solving",
    "technical design",
    "operational excellence",
    "process improvement",
    "tooling",
    "r&d",
}

SKILL_ALIASES = {
    "ml": "machine learning",
    "rag": "retrieval augmented generation",
    "llm": "large language models",
    "llms": "large language models",
    "api": "APIs",
    "apis": "APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "ci cd": "CI/CD",
    "ide": "IDEs",
    "ides": "IDEs",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "go": "Go",
    "golang": "Go",
    "mlflow": "MLflow",
    "nlp": "NLP",
    "genai": "generative ai",
    "js": "javascript",
    "node": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "postgres sql": "postgresql",
    "k8s": "kubernetes",
    "opentelemetry": "OpenTelemetry",
    "finops": "FinOps",
    "api design": "API design",
}


def _normalize_skill_key_without_aliases(skill: str) -> str:
    normalized = str(skill).strip().lower()
    normalized = re.sub(r"(?<=\w)\.(?=\w)", "", normalized)
    normalized = re.sub(r"[-_/]+", " ", normalized)
    normalized = re.sub(r"[^a-z0-9+#\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    tokens = [
        "api" if token == "apis" else token  # nosec
        for token in normalized.split()
    ]
    return " ".join(tokens)


def normalize_skill_text(skill: str) -> str:
    """Normalize skill-like text without collapsing aliases."""
    return _normalize_skill_key_without_aliases(skill)


def normalize_skill_key(skill: str) -> str:
    """Normalize one skill into the canonical comparison key used by matching."""
    normalized = _normalize_skill_key_without_aliases(skill)

    canonical = SKILL_ALIASES.get(normalized, normalized)

    if canonical == normalized:
        return normalized

    return _normalize_skill_key_without_aliases(canonical)


def normalize_skill_name(skill: str) -> str:
    """Normalize one extracted skill into a consistent dashboard-friendly name."""
    normalized = skill.strip().lower()
    normalized = _SEPARATOR_PATTERN.sub(" ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def normalize_skill_list(
    skills: list[str],
    max_skills: int = 20,
    exclude_generic_terms: bool = True,
) -> list[str]:
    """Normalize, deduplicate, and cap extracted skills."""
    normalized_skills: list[str] = []
    seen: set[str] = set()

    for skill in skills:
        if not isinstance(skill, str):
            continue

        normalized = normalize_skill_name(skill)

        if not normalized:
            continue

        if exclude_generic_terms and normalized in GENERIC_SKILL_TERMS:
            continue

        normalized = SKILL_ALIASES.get(normalized, normalized)

        if normalized in seen:
            continue

        seen.add(normalized)
        normalized_skills.append(normalized)

        if len(normalized_skills) >= max_skills:
            break

    return normalized_skills
