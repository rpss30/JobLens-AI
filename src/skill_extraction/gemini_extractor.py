"""Gemini-powered skill extraction for job descriptions.

This module is intentionally isolated from the production job processor for now.
We will test Gemini output quality before making AI extraction the default path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.skill_extraction.schema import (
    ExtractedSkill,
    SKILL_EXTRACTION_PROMPT_VERSION,
    build_structured_skill_extraction_prompt,
    parse_skill_extraction_json,
)


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class GeminiSkillExtractionResult:
    """Structured result returned by the Gemini skill extractor."""

    skills: list[str]
    raw_response: str
    skill_items: list[ExtractedSkill]
    model: str
    prompt_version: str


def build_skill_extraction_prompt(title: str, description: str) -> str:
    """Build a focused prompt for extracting job-relevant technical skills."""
    return build_structured_skill_extraction_prompt(
        title=title,
        description=description,
    )


def parse_gemini_skill_response(response_text: str, max_skills: int = 20) -> list[str]:
    """Parse Gemini JSON text into a normalized skill list."""
    try:
        return parse_skill_extraction_json(
            response_text,
            max_skills=max_skills,
        ).skills
    except ValueError as exc:
        message = str(exc).replace("Skill extraction response", "Gemini response")
        message = message.replace("Skill extraction JSON", "Gemini response JSON")
        raise ValueError(message) from exc


def extract_skills_with_gemini(
    title: str,
    description: str,
    model: str = DEFAULT_GEMINI_MODEL,
    max_skills: int = 20,
) -> GeminiSkillExtractionResult:
    """Extract skills from one job posting using Gemini."""
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=build_skill_extraction_prompt(title=title, description=description),
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "skills": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "confidence": {"type": "number"},
                                "evidence": {"type": "string"},
                            },
                            "required": ["name", "confidence", "evidence"],
                        },
                    }
                },
                "required": ["skills"],
            },
        ),
    )

    raw_response = response.text or ""
    parsed_response = parse_skill_extraction_json(
        raw_response,
        max_skills=max_skills,
    )

    return GeminiSkillExtractionResult(
        skills=parsed_response.skills,
        raw_response=raw_response,
        skill_items=parsed_response.skill_items,
        model=model,
        prompt_version=parsed_response.prompt_version,
    )
