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
}


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