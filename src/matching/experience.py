"""Experience-fit helpers for explaining job matches."""

from __future__ import annotations

import re
from dataclasses import dataclass


NO_CANDIDATE_EXPERIENCE = "Not specified"
# Unknown values normalize to NO_CANDIDATE_EXPERIENCE rather than raising, so
# every bucket a client can offer has to appear here or the answer is silently
# discarded and experience fit degrades to "Not specified".
EXPERIENCE_BUCKETS: dict[str, tuple[int, int | None]] = {
    "0-1 years": (0, 1),
    "1-2 years": (1, 2),
    "2-3 years": (2, 3),
    "3-4 years": (3, 4),
    "3-5 years": (3, 5),
    "4-5 years": (4, 5),
    "5-7 years": (5, 7),
    "5-8 years": (5, 8),
    "7-10 years": (7, 10),
    "8+ years": (8, None),
    "10+ years": (10, None),
}

_YEAR_REQUIREMENT_PATTERN = re.compile(
    r"(?P<minimum>\d{1,2})\s*(?:\+|(?:-|to)\s*\d{1,2})?\s*(?:years?|yrs?)",
    re.IGNORECASE,
)
_EXPERIENCE_TERM_PATTERN = re.compile(
    r"\b(experience|experienced|professional|industry|hands-on)\b",
    re.IGNORECASE,
)
_REQUIREMENT_CUE_PATTERN = re.compile(
    r"\b(required|requirement|requirements|qualification|qualifications|"
    r"minimum|min\.?|at least|must have|need|needs|needed|looking for|"
    r"you have|you bring|candidate|applicant|professional|hands-on|relevant)\b",
    re.IGNORECASE,
)
_NON_REQUIREMENT_CUE_PATTERN = re.compile(
    r"\b(company|startup|team|product|platform|founded|history|anniversary|"
    r"serving|customers|clients|business)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExperienceRequirement:
    years: int | None
    label: str
    source: str


@dataclass(frozen=True)
class ExperienceFit:
    candidate_experience: str
    required_experience: str
    required_experience_years: int | None
    experience_requirement_source: str
    experience_fit: str
    experience_fit_score: float | None


def normalize_candidate_experience_bucket(candidate_experience: str | None) -> str:
    """Return a supported candidate experience bucket or the neutral default."""
    cleaned_value = str(candidate_experience or "").strip()

    if cleaned_value in EXPERIENCE_BUCKETS:
        return cleaned_value

    return NO_CANDIDATE_EXPERIENCE


def extract_required_experience_years(description: object) -> int | None:
    """Extract explicit minimum experience years from requirement-like context."""
    text = re.sub(r"\s+", " ", str(description or "")).strip()

    if not text:
        return None

    required_years = []

    for match in _YEAR_REQUIREMENT_PATTERN.finditer(text):
        year_value = int(match.group("minimum"))

        if year_value > 15:
            continue

        window_start = max(0, match.start() - 90)
        window_end = min(len(text), match.end() + 120)
        context = text[window_start:window_end]

        if not _EXPERIENCE_TERM_PATTERN.search(context):
            continue

        has_requirement_cue = bool(_REQUIREMENT_CUE_PATTERN.search(context))
        has_non_requirement_cue = bool(_NON_REQUIREMENT_CUE_PATTERN.search(context))

        if has_requirement_cue or not has_non_requirement_cue:
            required_years.append(year_value)

    if not required_years:
        return None

    return max(required_years)


def infer_required_experience_from_level(
    experience_level: object,
) -> ExperienceRequirement:
    """Infer a minimum years requirement from the existing coarse level label."""
    level = str(experience_level or "").strip()
    normalized_level = level.lower()

    if not normalized_level or normalized_level == "any":
        return ExperienceRequirement(
            years=None,
            label="Requirement unclear",
            source="unknown",
        )

    if any(
        term in normalized_level
        for term in ["intern", "entry", "junior", "new grad"]
    ):
        return ExperienceRequirement(
            years=0,
            label=f"{level} inferred",
            source="experience_level",
        )

    if any(term in normalized_level for term in ["staff", "principal", "lead"]):
        return ExperienceRequirement(
            years=8,
            label=f"{level} inferred",
            source="experience_level",
        )

    if "senior" in normalized_level:
        return ExperienceRequirement(
            years=5,
            label=f"{level} inferred",
            source="experience_level",
        )

    if any(term in normalized_level for term in ["mid", "intermediate"]):
        return ExperienceRequirement(
            years=3,
            label=f"{level} inferred",
            source="experience_level",
        )

    return ExperienceRequirement(
        years=None,
        label="Requirement unclear",
        source="unknown",
    )


def get_experience_requirement(
    *,
    description: object,
    experience_level: object,
) -> ExperienceRequirement:
    explicit_years = extract_required_experience_years(description)

    if explicit_years is not None:
        return ExperienceRequirement(
            years=explicit_years,
            label=f"{explicit_years}+ years",
            source="description",
        )

    return infer_required_experience_from_level(experience_level)


def evaluate_experience_fit(
    *,
    candidate_experience: str | None,
    description: object,
    experience_level: object,
) -> ExperienceFit:
    candidate_bucket = normalize_candidate_experience_bucket(candidate_experience)
    requirement = get_experience_requirement(
        description=description,
        experience_level=experience_level,
    )

    if candidate_bucket == NO_CANDIDATE_EXPERIENCE:
        return ExperienceFit(
            candidate_experience=candidate_bucket,
            required_experience=requirement.label,
            required_experience_years=requirement.years,
            experience_requirement_source=requirement.source,
            experience_fit="Not assessed",
            experience_fit_score=None,
        )

    if requirement.years is None:
        return ExperienceFit(
            candidate_experience=candidate_bucket,
            required_experience=requirement.label,
            required_experience_years=None,
            experience_requirement_source=requirement.source,
            experience_fit="Requirement unclear",
            experience_fit_score=None,
        )

    candidate_min, candidate_max = EXPERIENCE_BUCKETS[candidate_bucket]

    if candidate_min >= requirement.years:
        fit_label = "Meets requirement"
        fit_score = 100.0
    elif candidate_max is None or candidate_max >= requirement.years:
        fit_label = "Close match"
        fit_score = 75.0
    elif requirement.years - candidate_max <= 2:
        fit_label = "Close match"
        fit_score = 65.0
    else:
        fit_label = "Stretch"
        fit_score = 40.0

    return ExperienceFit(
        candidate_experience=candidate_bucket,
        required_experience=requirement.label,
        required_experience_years=requirement.years,
        experience_requirement_source=requirement.source,
        experience_fit=fit_label,
        experience_fit_score=fit_score,
    )
