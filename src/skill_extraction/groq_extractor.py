"""Groq-powered skill extraction fallback for job descriptions."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from groq import Groq

from src.skill_extraction.gemini_extractor import build_skill_extraction_prompt
from src.skill_extraction.normalizer import normalize_skill_list


DEFAULT_GROQ_MODEL = "moonshotai/kimi-k2-instruct"


@dataclass(frozen=True)
class GroqSkillExtractionResult:
    """Structured result returned by the Groq skill extractor."""

    skills: list[str]
    raw_response: str


def parse_groq_skill_response(response_text: str, max_skills: int = 20) -> list[str]:
    """Parse Groq JSON text into a normalized skill list."""
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Groq response was not valid JSON.") from exc

    skills = payload.get("skills")

    if not isinstance(skills, list):
        raise ValueError("Groq response JSON must contain a 'skills' list.")

    return normalize_skill_list(skills, max_skills=max_skills)


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
                    "Return valid JSON only, with this shape: "
                    '{"skills": ["skill 1", "skill 2"]}.'
                ),
            },
            {
                "role": "user",
                "content": build_skill_extraction_prompt(
                    title=title,
                    description=description,
                ),
            },
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw_response = completion.choices[0].message.content or ""
    skills = parse_groq_skill_response(raw_response, max_skills=max_skills)

    return GroqSkillExtractionResult(skills=skills, raw_response=raw_response)