"""Groq-powered skill extraction fallback for job descriptions."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from groq import Groq

from src.skill_extraction.schema import (
    ExtractedSkill,
    SKILL_EXTRACTION_PROMPT_VERSION,
    build_structured_skill_extraction_prompt,
    parse_skill_extraction_json,
)


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


@dataclass(frozen=True)
class GroqSkillExtractionResult:
    """Structured result returned by the Groq skill extractor."""

    skills: list[str]
    raw_response: str
    skill_items: list[ExtractedSkill]
    model: str
    prompt_version: str


def parse_groq_skill_response(response_text: str, max_skills: int = 20) -> list[str]:
    """Parse Groq JSON text into a normalized skill list."""
    try:
        return parse_skill_extraction_json(
            response_text,
            max_skills=max_skills,
        ).skills
    except ValueError as exc:
        message = str(exc).replace("Skill extraction response", "Groq response")
        message = message.replace("Skill extraction JSON", "Groq response JSON")
        raise ValueError(message) from exc


def extract_skills_with_groq(
    title: str,
    description: str,
    model: str | None = None,
    max_skills: int = 20,
) -> GroqSkillExtractionResult:
    """Extract skills from one job posting using Groq."""
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set.")

    selected_model = model or os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)

    client = Groq(api_key=api_key)

    completion = client.chat.completions.create(
        model=selected_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract technical skills from job postings. "
                    "Return valid JSON only using the requested schema. "
                    f"Prompt version: {SKILL_EXTRACTION_PROMPT_VERSION}."
                ),
            },
            {
                "role": "user",
                "content": build_structured_skill_extraction_prompt(
                    title=title,
                    description=description,
                ),
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw_response = completion.choices[0].message.content or ""
    parsed_response = parse_skill_extraction_json(
        raw_response,
        max_skills=max_skills,
    )

    return GroqSkillExtractionResult(
        skills=parsed_response.skills,
        raw_response=raw_response,
        skill_items=parsed_response.skill_items,
        model=selected_model,
        prompt_version=parsed_response.prompt_version,
    )
