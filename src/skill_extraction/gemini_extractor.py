"""Gemini-powered skill extraction for job descriptions.

This module is intentionally isolated from the production job processor for now.
We will test Gemini output quality before making AI extraction the default path.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.skill_extraction.normalizer import normalize_skill_list


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


@dataclass(frozen=True)
class GeminiSkillExtractionResult:
    """Structured result returned by the Gemini skill extractor."""

    skills: list[str]
    raw_response: str


def build_skill_extraction_prompt(title: str, description: str) -> str:
    """Build a focused prompt for extracting job-relevant technical skills."""
    trimmed_description = description[:4000]

    return f"""
Extract technical skills from this job posting for a job market dashboard.

Rules:
- Extract only concrete technical skills, tools, platforms, programming languages, frameworks, libraries, databases, cloud services, engineering practices, and ML/data concepts.
- Do not include soft skills.
- Do not include generic words like team, communication, business, platform, customer, work, experience, leadership, collaboration, or problem solving.
- Do not include company names, locations, benefits, education requirements, job titles, or years of experience.
- Use normalized names where possible, such as Python, SQL, AWS, PostgreSQL, MySQL, PyTorch, TensorFlow, scikit-learn, Pandas, NumPy, Docker, Kubernetes, Terraform, REST APIs, CI/CD, MLflow, and model deployment.
- If no concrete technical skills are present, return an empty skills array.
- Keep each skill short.
- Do not invent skills from the job title alone unless the description strongly supports them.

Job title:
{title}

Job description:
{trimmed_description}
""".strip()


def parse_gemini_skill_response(response_text: str, max_skills: int = 20) -> list[str]:
    """Parse Gemini JSON text into a normalized skill list."""
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini response was not valid JSON.") from exc

    skills = payload.get("skills")

    if not isinstance(skills, list):
        raise ValueError("Gemini response JSON must contain a 'skills' list.")

    return normalize_skill_list(skills, max_skills=max_skills)


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
                        "items": {"type": "string"},
                    }
                },
                "required": ["skills"],
            },
        ),
    )

    raw_response = response.text or ""
    skills = parse_gemini_skill_response(raw_response, max_skills=max_skills)

    return GeminiSkillExtractionResult(skills=skills, raw_response=raw_response)