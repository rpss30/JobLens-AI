"""Groq-powered skill extraction fallback for job descriptions."""

from __future__ import annotations

import logging
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


logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
# Providers retire models on their own schedule. When the configured model is
# gone the whole ingestion run silently degrades to dictionary extraction, so a
# second model is tried before giving up.
DEFAULT_GROQ_MODEL_FALLBACKS = ("openai/gpt-oss-120b",)

# Models this process has already seen reported as retired. Without this, every
# posting in a run would pay for the same failed call.
_unavailable_models: set[str] = set()


def reset_unavailable_models() -> None:
    """Forget which models were reported as retired."""
    _unavailable_models.clear()


def parse_model_list(value: str | None) -> list[str]:
    return [model.strip() for model in (value or "").split(",") if model.strip()]


def get_groq_model_candidates(model: str | None = None) -> list[str]:
    """Return the models to try in order.

    An explicitly passed model is used alone: a caller pinning a model wants to
    know when it is unavailable rather than silently receive another one.
    """
    if model:
        return [model]

    primary = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
    fallbacks = parse_model_list(os.getenv("GROQ_MODEL_FALLBACKS")) or list(
        DEFAULT_GROQ_MODEL_FALLBACKS
    )

    ordered: list[str] = []

    for candidate in [primary, *fallbacks]:
        if candidate not in ordered:
            ordered.append(candidate)

    return ordered


def is_model_unavailable_error(error: Exception) -> bool:
    """True when the provider says the model is gone rather than the call failed.

    Groq answers a retired model with 404 `model_not_found`. Anything else, such
    as a rate limit or a timeout, is a problem with this call and must not
    disqualify the model for the rest of the run.
    """
    message = str(error).lower()

    return "model_not_found" in message or "does not exist" in message


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

    candidates = get_groq_model_candidates(model)
    client = Groq(api_key=api_key)
    attempted: list[str] = []

    for candidate in candidates:
        if candidate in _unavailable_models:
            continue

        attempted.append(candidate)

        try:
            completion = client.chat.completions.create(
                model=candidate,
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
        except Exception as error:
            if not is_model_unavailable_error(error):
                raise

            _unavailable_models.add(candidate)
            logger.warning(
                "Groq model %s is unavailable; falling back to the next model.",
                candidate,
            )
            continue

        raw_response = completion.choices[0].message.content or ""
        parsed_response = parse_skill_extraction_json(
            raw_response,
            max_skills=max_skills,
        )

        return GroqSkillExtractionResult(
            skills=parsed_response.skills,
            raw_response=raw_response,
            skill_items=parsed_response.skill_items,
            # The model that answered, not the one that was asked for first, so
            # the snapshot records which model produced each extraction.
            model=candidate,
            prompt_version=parsed_response.prompt_version,
        )

    raise RuntimeError(
        "No configured Groq model is available. Tried: "
        + ", ".join(attempted or candidates)
        + ". Set GROQ_MODEL or GROQ_MODEL_FALLBACKS to a model the account can use."
    )
