# src/matching/match_engine.py

import pandas as pd


def normalize_skill(skill: str) -> str:
    """Normalize skill names for comparison."""
    return skill.strip().lower()


def calculate_match_score(user_skills: list[str], required_skills: list[str]) -> float:
    """Calculate percentage match between user skills and job required skills."""
    if not required_skills:
        return 0.0

    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    matched_skills = user_skill_set.intersection(required_skill_set)
    score = len(matched_skills) / len(required_skill_set)

    return round(score * 100, 2)


def get_missing_skills(user_skills: list[str], required_skills: list[str]) -> list[str]:
    """Return skills required by the market that the user does not have."""
    user_skill_set = {normalize_skill(skill) for skill in user_skills}
    required_skill_set = {normalize_skill(skill) for skill in required_skills}

    missing = required_skill_set - user_skill_set
    return sorted(missing)


def get_top_skills(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Count most common extracted skills across jobs."""
    all_skills = []

    for skills in df["extracted_skills"]:
        if isinstance(skills, list):
            all_skills.extend(skills)

    skill_counts = pd.Series(all_skills).value_counts().head(top_n)

    return pd.DataFrame({
        "skill": skill_counts.index,
        "count": skill_counts.values,
    })


def score_roles(df: pd.DataFrame, user_skills: list[str]) -> pd.DataFrame:
    """Calculate average match score for each role category."""
    role_scores = []

    for role_category, group in df.groupby("role_category"):
        role_required_skills = set()

        for skills in group["extracted_skills"]:
            if isinstance(skills, list):
                role_required_skills.update(skills)

        score = calculate_match_score(user_skills, list(role_required_skills))
        missing_skills = get_missing_skills(user_skills, list(role_required_skills))

        role_scores.append(
            {
                "role_category": role_category,
                "match_score": score,
                "required_skills": sorted(role_required_skills),
                "missing_skills": missing_skills,
            }
        )

    return pd.DataFrame(role_scores).sort_values(
        by="match_score",
        ascending=False,
    )