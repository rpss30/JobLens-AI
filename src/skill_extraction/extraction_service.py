"""AI-first skill extraction service.

Current behavior:
1. Try Gemini first.
2. If Gemini fails, use the existing deterministic extractor as an emergency fallback.

Later:
- Add Groq between Gemini and deterministic fallback.
"""

from __future__ import annotations

import time

from dataclasses import dataclass

from src.processing.job_processor import extract_skills as extract_skills_deterministic
from src.skill_extraction.gemini_extractor import extract_skills_with_gemini


GEMINI_PROVIDER = "gemini"
DETERMINISTIC_PROVIDER = "deterministic_fallback"


@dataclass(frozen=True)
class SkillExtractionServiceResult:
    """Result from the AI-first skill extraction service."""

    skills: list[str]
    provider: str
    error: str


def extract_skills_ai_first(
    title: str,
    description: str,
    use_deterministic_fallback: bool = True,
    max_gemini_attempts: int = 2,
    retry_delay_seconds: int = 5,
) -> SkillExtractionServiceResult:
    """Extract skills using Gemini first, then deterministic fallback if needed."""
    gemini_errors: list[str] = []

    for attempt in range(1, max_gemini_attempts + 1):
        try:
            gemini_result = extract_skills_with_gemini(
                title=title,
                description=description,
            )

            return SkillExtractionServiceResult(
                skills=gemini_result.skills,
                provider=GEMINI_PROVIDER,
                error="",
            )

        except Exception as exc:
            gemini_error = f"Attempt {attempt}: {type(exc).__name__}: {exc}"
            gemini_errors.append(gemini_error)

            if attempt < max_gemini_attempts:
                time.sleep(retry_delay_seconds)

    combined_error = " | ".join(gemini_errors)

    if not use_deterministic_fallback:
        return SkillExtractionServiceResult(
            skills=[],
            provider=GEMINI_PROVIDER,
            error=combined_error,
        )

    fallback_skills = extract_skills_deterministic(description)

    return SkillExtractionServiceResult(
        skills=fallback_skills,
        provider=DETERMINISTIC_PROVIDER,
        error=combined_error,
    )