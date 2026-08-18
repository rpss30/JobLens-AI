"""Heuristics for classifying extracted skills as required or preferred."""

from __future__ import annotations

import re

from src.skill_extraction.normalizer import (
    SKILL_ALIASES,
    normalize_skill_key,
    normalize_skill_text,
)


REQUIRED_SKILL = "required"
PREFERRED_SKILL = "preferred"
UNKNOWN_SKILL_REQUIREMENT = "unknown"
PREFERRED_SKILL_WEIGHT_MULTIPLIER = 0.5

_REQUIRED_CONTEXT_PATTERN = re.compile(
    r"\b(required|required qualifications?|requirements?|must have|need|needs|"
    r"minimum|min\.?|at least|you have|you bring|we expect|candidate has|"
    r"applicant has|strong experience|proficiency|proficient|expertise)\b",
    re.IGNORECASE,
)
_PREFERRED_CONTEXT_PATTERN = re.compile(
    r"\b(preferred|nice to have|nice-to-have|bonus|bonus points?|plus|"
    r"asset|an asset|would be great|desired|familiarity|exposure to|"
    r"optional|ideal|ideally)\b",
    re.IGNORECASE,
)


def _skill_search_phrases(skill: str) -> list[str]:
    normalized_skill = normalize_skill_key(skill)
    phrases = {normalize_skill_text(skill), normalized_skill}

    for alias, canonical in SKILL_ALIASES.items():
        if normalize_skill_key(canonical) == normalized_skill:
            phrases.add(normalize_skill_text(alias))
            phrases.add(normalize_skill_text(canonical))

    return sorted(
        {phrase for phrase in phrases if phrase},
        key=lambda value: (-len(value), value),
    )


def _find_phrase_contexts(
    description: object,
    phrases: list[str],
) -> list[tuple[str, int, int]]:
    raw_description = re.sub(r"\s+", " ", str(description or "")).strip()

    if not raw_description:
        return []

    contexts = []

    for raw_segment in re.split(r"[.;•]+", raw_description):
        segment = normalize_skill_text(raw_segment)

        if not segment:
            continue

        for phrase in phrases:
            phrase_pattern = r"\s+".join(re.escape(part) for part in phrase.split())
            pattern = re.compile(
                rf"(?<![a-z0-9+#]){phrase_pattern}(?![a-z0-9+#])",
                re.IGNORECASE,
            )

            for match in pattern.finditer(segment):
                contexts.append((segment, match.start(), match.end()))

    return contexts


def _nearest_cue_distance(
    pattern: re.Pattern[str],
    context: str,
    skill_start: int,
    skill_end: int,
) -> int | None:
    distances = []

    for match in pattern.finditer(context):
        if match.end() <= skill_start:
            distances.append(skill_start - match.end())
        elif match.start() >= skill_end:
            distances.append(match.start() - skill_end)
        else:
            distances.append(0)

    return min(distances) if distances else None


def classify_skill_requirement(skill: str, description: object) -> str:
    """Classify one extracted skill from nearby job-description wording."""
    contexts = _find_phrase_contexts(description, _skill_search_phrases(skill))

    if not contexts:
        return UNKNOWN_SKILL_REQUIREMENT

    preferred_distance: int | None = None
    required_distance: int | None = None

    for context, skill_start, skill_end in contexts:
        context_preferred_distance = _nearest_cue_distance(
            _PREFERRED_CONTEXT_PATTERN,
            context,
            skill_start,
            skill_end,
        )
        context_required_distance = _nearest_cue_distance(
            _REQUIRED_CONTEXT_PATTERN,
            context,
            skill_start,
            skill_end,
        )

        if context_preferred_distance is not None:
            preferred_distance = (
                context_preferred_distance
                if preferred_distance is None
                else min(preferred_distance, context_preferred_distance)
            )

        if context_required_distance is not None:
            required_distance = (
                context_required_distance
                if required_distance is None
                else min(required_distance, context_required_distance)
            )

    if preferred_distance is not None and (
        required_distance is None or preferred_distance < required_distance
    ):
        return PREFERRED_SKILL

    if required_distance is not None:
        return REQUIRED_SKILL

    return UNKNOWN_SKILL_REQUIREMENT


def classify_job_skill_requirements(
    skills: list[str],
    description: object,
) -> dict[str, str]:
    """Return normalized skill keys mapped to required/preferred/unknown."""
    return {
        normalized_skill: classify_skill_requirement(skill, description)
        for skill in skills
        if (normalized_skill := normalize_skill_key(skill))
    }


def requirement_weight_multiplier(requirement_type: str) -> float:
    """Return the score multiplier for a requirement classification."""
    if requirement_type == PREFERRED_SKILL:
        return PREFERRED_SKILL_WEIGHT_MULTIPLIER

    return 1.0


def summarize_skill_requirement(
    skill: str,
    descriptions: list[object],
) -> dict[str, int | str]:
    """
    Roll up how postings treat one skill: as a must-have, or a nice-to-have.

    Deliberately cautious. The classifier reads cue words near the skill and
    often finds none, so a verdict is only given when the classified mentions
    agree clearly. When most mentions are unreadable the answer is "unclear"
    rather than a guess dressed up as a finding.
    """
    counts = {REQUIRED_SKILL: 0, PREFERRED_SKILL: 0, UNKNOWN_SKILL_REQUIREMENT: 0}

    for description in descriptions:
        counts[classify_skill_requirement(skill, description)] += 1

    required = counts[REQUIRED_SKILL]
    preferred = counts[PREFERRED_SKILL]
    classified = required + preferred
    total = classified + counts[UNKNOWN_SKILL_REQUIREMENT]

    if total == 0 or classified * 2 < total:
        signal = "unclear"
    elif required >= classified * 0.6:
        signal = "required"
    elif preferred >= classified * 0.6:
        signal = "preferred"
    else:
        signal = "mixed"

    return {
        "required_count": required,
        "preferred_count": preferred,
        "unclear_count": counts[UNKNOWN_SKILL_REQUIREMENT],
        "requirement_signal": signal,
    }
