"""AI-first skill extraction service.

Current behavior:
1. Try Groq first.
2. If Groq fails, try Gemini.
3. If both providers fail, use deterministic extraction as an emergency fallback.
"""

from __future__ import annotations

import time

from dataclasses import dataclass

from src.processing.job_processor import extract_skills as extract_skills_deterministic
from src.skill_extraction.gemini_extractor import extract_skills_with_gemini
from src.skill_extraction.groq_extractor import extract_skills_with_groq
from src.skill_extraction.schema import ExtractedSkill


GEMINI_PROVIDER = "gemini"
GROQ_PROVIDER = "groq"
DETERMINISTIC_PROVIDER = "deterministic_fallback"


@dataclass(frozen=True)
class SkillExtractionServiceResult:
    """Result from the AI-first skill extraction service."""

    skills: list[str]
    provider: str
    error: str
    raw_response: str = ""
    model: str = ""
    prompt_version: str = ""
    skill_items: list[ExtractedSkill] | None = None


def extract_skills_ai_first(
    title: str,
    description: str,
    use_groq_primary: bool = True,
    use_gemini_fallback: bool = True,
    use_deterministic_fallback: bool = True,
    max_groq_attempts: int = 1,
    max_gemini_attempts: int = 1,
    retry_delay_seconds: int = 5,
) -> SkillExtractionServiceResult:
    """Extract skills using Groq first, then Gemini, then deterministic fallback."""
    errors: list[str] = []

    if use_groq_primary:
        for attempt in range(1, max_groq_attempts + 1):
            try:
                groq_result = extract_skills_with_groq(
                    title=title,
                    description=description,
                )

                return SkillExtractionServiceResult(
                    skills=groq_result.skills,
                    provider=GROQ_PROVIDER,
                    error="",
                    raw_response=getattr(groq_result, "raw_response", ""),
                    model=getattr(groq_result, "model", ""),
                    prompt_version=getattr(groq_result, "prompt_version", ""),
                    skill_items=getattr(groq_result, "skill_items", None),
                )

            except Exception as exc:
                errors.append(f"Groq attempt {attempt}: {type(exc).__name__}: {exc}")

                if attempt < max_groq_attempts:
                    time.sleep(retry_delay_seconds)

    if use_gemini_fallback:
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
                    raw_response=getattr(gemini_result, "raw_response", ""),
                    model=getattr(gemini_result, "model", ""),
                    prompt_version=getattr(gemini_result, "prompt_version", ""),
                    skill_items=getattr(gemini_result, "skill_items", None),
                )

            except Exception as exc:
                errors.append(f"Gemini attempt {attempt}: {type(exc).__name__}: {exc}")

                if attempt < max_gemini_attempts:
                    time.sleep(retry_delay_seconds)

    combined_error = " | ".join(errors)

    if not use_deterministic_fallback:
        failed_provider = GEMINI_PROVIDER if use_gemini_fallback else GROQ_PROVIDER

        return SkillExtractionServiceResult(
            skills=[],
            provider=failed_provider,
            error=combined_error,
        )

    fallback_skills = extract_skills_deterministic(description)

    return SkillExtractionServiceResult(
        skills=fallback_skills,
        provider=DETERMINISTIC_PROVIDER,
        error=combined_error,
    )
