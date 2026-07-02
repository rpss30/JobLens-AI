"""Structured skill extraction contracts shared by LLM providers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.skill_extraction.normalizer import (
    GENERIC_SKILL_TERMS,
    SKILL_ALIASES,
    normalize_skill_name,
)


SKILL_EXTRACTION_PROMPT_VERSION = "skill-extraction-v2"


@dataclass(frozen=True)
class ExtractedSkill:
    """One normalized skill with optional model-provided metadata."""

    name: str
    confidence: float
    evidence: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class StructuredSkillExtraction:
    """Validated skills plus metadata from an LLM extraction response."""

    skills: list[str]
    skill_items: list[ExtractedSkill]
    prompt_version: str = SKILL_EXTRACTION_PROMPT_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "skills": self.skills,
            "skill_items": [item.to_dict() for item in self.skill_items],
            "prompt_version": self.prompt_version,
        }


def clamp_confidence(value: object, default: float = 1.0) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = default

    return max(0.0, min(1.0, confidence))


def normalize_taxonomy_skill_name(value: object) -> str:
    if not isinstance(value, str):
        return ""

    normalized = normalize_skill_name(value)

    if not normalized or normalized in GENERIC_SKILL_TERMS:
        return ""

    return SKILL_ALIASES.get(normalized, normalized)


def parse_skill_item(value: object) -> ExtractedSkill | None:
    """Parse one legacy string or structured skill object."""
    if isinstance(value, str):
        name = normalize_taxonomy_skill_name(value)
        return ExtractedSkill(name=name, confidence=1.0) if name else None

    if not isinstance(value, dict):
        return None

    raw_name = value.get("name") or value.get("skill")
    name = normalize_taxonomy_skill_name(raw_name)

    if not name:
        return None

    evidence = value.get("evidence") or ""

    return ExtractedSkill(
        name=name,
        confidence=clamp_confidence(value.get("confidence"), default=0.8),
        evidence=str(evidence).strip(),
    )


def parse_skill_extraction_payload(
    payload: dict[str, Any],
    *,
    max_skills: int = 20,
) -> StructuredSkillExtraction:
    skills = payload.get("skills")

    if not isinstance(skills, list):
        raise ValueError("Skill extraction JSON must contain a 'skills' list.")

    parsed_items: list[ExtractedSkill] = []
    seen_names: set[str] = set()

    for raw_skill in skills:
        item = parse_skill_item(raw_skill)

        if item is None or item.name in seen_names:
            continue

        seen_names.add(item.name)
        parsed_items.append(item)

        if len(parsed_items) >= max_skills:
            break

    return StructuredSkillExtraction(
        skills=[item.name for item in parsed_items],
        skill_items=parsed_items,
    )


def parse_skill_extraction_json(
    response_text: str,
    *,
    max_skills: int = 20,
) -> StructuredSkillExtraction:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Skill extraction response was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError("Skill extraction response must be a JSON object.")

    return parse_skill_extraction_payload(payload, max_skills=max_skills)


def build_structured_skill_extraction_prompt(title: str, description: str) -> str:
    """Build a versioned prompt for extracting job-relevant technical skills."""
    trimmed_description = description[:4000]

    return f"""
Extract technical skills from this job posting for a job market dashboard.

Prompt version: {SKILL_EXTRACTION_PROMPT_VERSION}

Return valid JSON only with this exact shape:
{{
  "skills": [
    {{"name": "Python", "confidence": 0.95, "evidence": "short phrase"}}
  ]
}}

Rules:
- Extract only concrete technical skills, tools, platforms, programming languages, frameworks, libraries, databases, cloud services, engineering practices, and ML/data concepts.
- Do not include soft skills.
- Do not include generic words like team, communication, business, platform, customer, work, experience, leadership, collaboration, or problem solving.
- Do not include company names, locations, benefits, education requirements, job titles, or years of experience.
- Use normalized names where possible, such as Python, SQL, AWS, PostgreSQL, MySQL, PyTorch, TensorFlow, scikit-learn, Pandas, NumPy, Docker, Kubernetes, Terraform, REST APIs, CI/CD, MLflow, and model deployment.
- Confidence must be a number from 0 to 1 based on explicit evidence in the description.
- Evidence must be a short phrase copied or paraphrased from the job description.
- If no concrete technical skills are present, return an empty skills array.
- Keep each skill short.
- Do not invent skills from the job title alone unless the description strongly supports them.

Job title:
{title}

Job description:
{trimmed_description}
""".strip()
