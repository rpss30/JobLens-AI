# src/matching/match_engine.py

import pandas as pd
from src.config.skills import BASE_SKILL_IMPORTANCE


def normalize_skill(skill: str) -> str:
    """Normalize skill names for comparison."""
    return skill.strip().lower()

def get_base_skill_importance(skill: str) -> int:
    """Fallback importance for small datasets."""
    return BASE_SKILL_IMPORTANCE.get(normalize_skill(skill), 2)

def frequency_to_weight(frequency: float) -> int:
    """Convert skill frequency into an importance weight from 1 to 5."""
    if frequency >= 0.75:
        return 5
    if frequency >= 0.50:
        return 4
    if frequency >= 0.30:
        return 3
    if frequency >= 0.15:
        return 2
    return 1

def get_max_weight_for_sample_size(total_jobs: int) -> int:
    """Limit max skill weight when a role category has too few jobs."""
    if total_jobs <= 2:
        return 3
    if total_jobs <= 4:
        return 4
    return 5

def build_role_skill_weights(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """
    Build role-specific skill weights.

    Example output:
    {
        "AI/ML": {"python": 5, "pytorch": 4, "docker": 2},
        "Cloud/AWS": {"aws": 5, "terraform": 4, "python": 2}
    }
    """
    role_weights = {}

    for role_category, group in df.groupby("role_category"):
        total_jobs = len(group)
        skill_job_counts = {}

        for skills in group["extracted_skills"]:
            if not isinstance(skills, list):
                continue

            # Count each skill only once per job using sets
            unique_skills = {normalize_skill(skill) for skill in skills}

            for skill in unique_skills:
                skill_job_counts[skill] = skill_job_counts.get(skill, 0) + 1

        weights = {}

        max_weight = get_max_weight_for_sample_size(total_jobs)

        for skill, count in skill_job_counts.items():
            frequency = count / total_jobs
            raw_weight = frequency_to_weight(frequency)
            base_weight = get_base_skill_importance(skill)

            # Blend market frequency with base importance to prevent all weights from becoming equal
            blended_weight = round((0.7 * raw_weight) + (0.3 * base_weight))

            # Smoothing to prevent tiny samples from giving every skill max weight
            weights[skill] = min(blended_weight, max_weight)

        role_weights[role_category] = weights

    return role_weights


def get_skill_weight_for_role(
    skill: str,
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
) -> int:
    """Get a skill's weight for a specific role category."""
    normalized_skill = normalize_skill(skill)

    return role_skill_weights.get(role_category, {}).get(normalized_skill, 1)


def calculate_role_match_score(
    user_skills: list[str],
    required_skills: list[str],
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
) -> tuple[float, int, int]:
    """Calculate weighted role match score for one role category."""
    if not required_skills:
        return 0.0, 0, 0

    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    total_possible_weight = sum(
        get_skill_weight_for_role(skill, role_category, role_skill_weights)
        for skill in required_skill_set
    )

    matched_weight = sum(
        get_skill_weight_for_role(skill, role_category, role_skill_weights)
        for skill in required_skill_set
        if skill in user_skill_set
    )

    if total_possible_weight == 0:
        return 0.0, matched_weight, total_possible_weight

    score = round((matched_weight / total_possible_weight) * 100, 2)

    return score, matched_weight, total_possible_weight


def calculate_unweighted_match_score(
    user_skills: list[str],
    required_skills: list[str],
) -> float:
    """Calculate simple percentage score for comparison."""
    if not required_skills:
        return 0.0

    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    matched_skills = user_skill_set.intersection(required_skill_set)

    return round((len(matched_skills) / len(required_skill_set)) * 100, 2)


def get_matched_skills(
    user_skills: list[str],
    required_skills: list[str],
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
) -> list[str]:
    """Return matched skills sorted by role-specific importance."""
    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    matched = user_skill_set.intersection(required_skill_set)

    return sorted(
        matched,
        key=lambda skill: get_skill_weight_for_role(
            skill,
            role_category,
            role_skill_weights,
        ),
        reverse=True,
    )


def get_missing_skills(
    user_skills: list[str],
    required_skills: list[str],
    role_category: str,
    role_skill_weights: dict[str, dict[str, int]],
) -> list[str]:
    """Return missing skills sorted by role-specific importance."""
    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    missing = required_skill_set - user_skill_set

    return sorted(
        missing,
        key=lambda skill: get_skill_weight_for_role(
            skill,
            role_category,
            role_skill_weights,
        ),
        reverse=True,
    )


def get_top_skills(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Count most common extracted skills across jobs."""
    all_skills = []

    for skills in df["extracted_skills"]:
        if isinstance(skills, list):
            all_skills.extend(skills)

    if not all_skills:
        return pd.DataFrame(columns=["skill", "count"])

    skill_counts = pd.Series(all_skills).value_counts().head(top_n)

    return pd.DataFrame({
        "skill": skill_counts.index,
        "count": skill_counts.values,
    })


def get_role_weighted_top_skills(
    df: pd.DataFrame,
    role_skill_weights: dict[str, dict[str, int]],
    top_n: int = 10,
) -> pd.DataFrame:
    """Rank skills by role-specific weighted importance."""
    rows = []

    for role_category, group in df.groupby("role_category"):
        skill_counts = {}

        for skills in group["extracted_skills"]:
            if not isinstance(skills, list):
                continue

            for skill in skills:
                normalized_skill = normalize_skill(skill)
                skill_counts[normalized_skill] = skill_counts.get(normalized_skill, 0) + 1

        for skill, count in skill_counts.items():
            weight = get_skill_weight_for_role(
                skill,
                role_category,
                role_skill_weights,
            )

            rows.append({
                "role_category": role_category,
                "skill": skill,
                "count": count,
                "role_weight": weight,
                "weighted_importance": count * weight,
            })

    if not rows:
        return pd.DataFrame(
            columns=[
                "role_category",
                "skill",
                "count",
                "role_weight",
                "weighted_importance",
            ]
        )

    return (
        pd.DataFrame(rows)
        .sort_values(by="weighted_importance", ascending=False)
        .head(top_n)
    )


def score_roles(df: pd.DataFrame, user_skills: list[str]) -> pd.DataFrame:
    """Calculate role-specific weighted match scores."""
    role_skill_weights = build_role_skill_weights(df)
    role_scores = []

    for role_category, group in df.groupby("role_category"):
        role_required_skills = set()

        for skills in group["extracted_skills"]:
            if isinstance(skills, list):
                role_required_skills.update(normalize_skill(skill) for skill in skills)

        required_skills = sorted(role_required_skills)

        weighted_score, matched_weight, total_possible_weight = calculate_role_match_score(
            user_skills=user_skills,
            required_skills=required_skills,
            role_category=role_category,
            role_skill_weights=role_skill_weights,
        )

        unweighted_score = calculate_unweighted_match_score(
            user_skills=user_skills,
            required_skills=required_skills,
        )

        matched_skills = get_matched_skills(
            user_skills=user_skills,
            required_skills=required_skills,
            role_category=role_category,
            role_skill_weights=role_skill_weights,
        )

        missing_skills = get_missing_skills(
            user_skills=user_skills,
            required_skills=required_skills,
            role_category=role_category,
            role_skill_weights=role_skill_weights,
        )

        role_scores.append({
            "role_category": role_category,
            "sample_size": len(group),
            "weighted_match_score": weighted_score,
            "unweighted_match_score": unweighted_score,
            "matched_weight": matched_weight,
            "total_possible_weight": total_possible_weight,
            "required_skills": required_skills,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "role_skill_weights": role_skill_weights.get(role_category, {}),
        })

    return pd.DataFrame(role_scores).sort_values(
        by="weighted_match_score",
        ascending=False,
    )