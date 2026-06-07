# src/dashboard/services.py

import pandas as pd
import streamlit as st

from src.processing.job_processor import process_jobs


RAW_DATA_PATH = "data/raw/sample_jobs.csv"
PROCESSED_DATA_PATH = "data/processed/processed_jobs.csv"


@st.cache_data
def load_processed_jobs() -> pd.DataFrame:
    """Load and process job data once."""
    return process_jobs(
        input_path=RAW_DATA_PATH,
        output_path=PROCESSED_DATA_PATH,
    )


def filter_jobs(
    df: pd.DataFrame,
    target_roles: list[str],
    location: str,
    experience_level: str,
) -> pd.DataFrame:
    """
    Filter jobs based on user input.

    Filtering is intentionally flexible because sample datasets often have
    slightly different formats for location and experience level.
    """
    filtered_df = df.copy()

    if target_roles:
        role_keywords = [
            role.strip().lower()
            for role in target_roles
            if role.strip()
        ]

        def title_matches(clean_title: str) -> bool:
            clean_title = str(clean_title).lower()

            for role in role_keywords:
                role_words = role.split()

                # Full phrase match first
                if role in clean_title:
                    return True

                # Fallback: match if at least one important role word appears
                important_words = [
                    word for word in role_words
                    if word not in {"junior", "senior", "entry", "level"}
                ]

                if any(word in clean_title for word in important_words):
                    return True

            return False

        filtered_df = filtered_df[
            filtered_df["clean_title"].apply(title_matches)
        ]

    if location and location != "Any":
        location_lower = location.strip().lower()

        # "Toronto, ON" should still match "Toronto" or "Toronto ON"
        location_parts = [
            part.strip()
            for part in location_lower.replace(",", " ").split()
            if part.strip()
        ]

        filtered_df = filtered_df[
            filtered_df["location"]
            .astype(str)
            .str.lower()
            .apply(
                lambda job_location: any(
                    part in job_location
                    for part in location_parts
                )
            )
        ]

    if experience_level and experience_level != "Any":
        selected_experience = (
            experience_level
            .lower()
            .replace("-", " ")
            .strip()
        )

        filtered_df = filtered_df[
            filtered_df["experience_level"]
            .astype(str)
            .str.lower()
            .str.replace("-", " ", regex=False)
            .str.strip()
            .str.contains(selected_experience, na=False)
        ]

    return filtered_df

def get_available_target_roles(df: pd.DataFrame) -> list[str]:
    """
    Return a sorted list of job titles available in the dataset.
    These are used as selectable target roles in the sidebar.
    """

    if df.empty or "title" not in df.columns:
        return []

    return sorted(
        df["title"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


def get_available_skills(df: pd.DataFrame) -> list[str]:
    """
    Return a sorted list of skills extracted from the processed job dataset.
    These are used as selectable current skills in the sidebar.
    """

    if df.empty or "extracted_skills" not in df.columns:
        return []

    skills = set()

    for raw_skills in df["extracted_skills"].dropna():
        if isinstance(raw_skills, list):
            skill_list = raw_skills
        elif isinstance(raw_skills, str):
            skill_list = [
                skill.strip()
                for skill in raw_skills.split(",")
                if skill.strip()
            ]
        else:
            skill_list = []

        for skill in skill_list:
            skills.add(skill.strip())

    return sorted(skills)

def get_available_locations(df: pd.DataFrame) -> list[str]:
    """
    Return a sorted list of locations available in the dataset.
    These are used as selectable location options in the sidebar.
    """

    if df.empty or "location" not in df.columns:
        return []

    return sorted(
        df["location"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

def get_top_companies(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Return companies with the most matching jobs."""
    company_counts = df["company"].value_counts().head(top_n)

    return pd.DataFrame({
        "company": company_counts.index,
        "job_count": company_counts.values,
    })

def get_jobs_by_location(df: pd.DataFrame) -> pd.DataFrame:
    """Return job counts grouped by location."""

    if df.empty or "location" not in df.columns:
        return pd.DataFrame(columns=["location", "job_count"])

    location_counts_df = (
        df["location"]
        .dropna()
        .astype(str)
        .value_counts()
        .reset_index()
    )

    location_counts_df.columns = ["location", "job_count"]

    return location_counts_df.sort_values(
        by="job_count",
        ascending=False,
    )

def get_learning_priorities(
    role_scores_df: pd.DataFrame,
    filtered_jobs: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rank missing skills by weighted market opportunity.

    priority_score = sum(role weight for missing skill across roles) * job demand
    """
    rows = []

    skill_job_counts = {}

    for _, job in filtered_jobs.iterrows():
        job_skills_raw = job.get("extracted_skills", [])
        job_skills = []

        if isinstance(job_skills_raw, list):
            job_skills = job_skills_raw
        elif isinstance(job_skills_raw, str):
            job_skills = [skill.strip() for skill in job_skills_raw.split(",") if skill.strip()]

        for skill in set(job_skills):
            skill_job_counts[skill] = skill_job_counts.get(skill, 0) + 1

    for _, row in role_scores_df.iterrows():
        role_category = row["role_category"]
        role_weights = row["role_skill_weights"]

        for skill in row["missing_skills"]:
            weight = role_weights.get(skill, 1)
            market_demand = skill_job_counts.get(skill, 1)

            rows.append({
                "skill": skill,
                "role_category": role_category,
                "weight": weight,
                "market_demand": market_demand,
                "priority_score": weight * market_demand,
            })

    if not rows:
        return pd.DataFrame(
            columns=[
                "skill",
                "roles_missing_for",
                "market_demand",
                "total_priority_score",
            ]
        )

    priorities_df = pd.DataFrame(rows)

    grouped_df = (
        priorities_df
        .groupby("skill")
        .agg(
            roles_missing_for=("role_category", lambda roles: ", ".join(sorted(set(roles)))),
            market_demand=("market_demand", "max"),
            total_priority_score=("priority_score", "sum"),
        )
        .reset_index()
        .sort_values(by="total_priority_score", ascending=False)
    )

    return grouped_df

def get_tag_placeholder(
    session_key: str,
    default_tags: list[str],
    placeholder: str,
) -> str:
    """Show placeholder only when the tag input is empty."""
    current_tags = st.session_state.get(session_key, default_tags)

    if current_tags:
        return ""

    return placeholder


def get_score_summary_metrics(
    filtered_jobs: pd.DataFrame,
    role_scores_df: pd.DataFrame,
    user_skills: list[str],
) -> dict:
    """Build top-level summary metrics for the dashboard."""
    best_role = (
        role_scores_df.iloc[0]["role_category"]
        if not role_scores_df.empty else "N/A"
    )

    avg_weighted_score = (
        round(role_scores_df["weighted_match_score"].mean(), 2)
        if not role_scores_df.empty else 0.0
    )

    return {
        "matching_jobs": len(filtered_jobs),
        "role_categories": filtered_jobs["role_category"].nunique(),
        "average_match": avg_weighted_score,
        "current_skills": len(user_skills),
        "best_role": best_role,
    }

def get_job_match_details(
    filtered_jobs: pd.DataFrame,
    user_skills: list[str],
) -> pd.DataFrame:
    """Build job-level match details for matching job postings."""
    normalized_user_skills = {skill.strip().lower() for skill in user_skills if skill.strip()}

    rows = []

    for _, row in filtered_jobs.iterrows():
        job_skills_raw = row.get("extracted_skills", [])
        job_skills = []

        if isinstance(job_skills_raw, list):
            job_skills = job_skills_raw
        elif isinstance(job_skills_raw, str):
            job_skills = [skill.strip() for skill in job_skills_raw.split(",") if skill.strip()]

        normalized_job_skills = [skill.strip().lower() for skill in job_skills]

        matched_skills = [
            skill for skill, normalized in zip(job_skills, normalized_job_skills)
            if normalized in normalized_user_skills
        ]

        missing_skills = [
            skill for skill, normalized in zip(job_skills, normalized_job_skills)
            if normalized not in normalized_user_skills
        ]

        total_skills = len(normalized_job_skills)
        match_score = round((len(matched_skills) / total_skills) * 100, 2) if total_skills else 0.0

        rows.append({
            "title": row["title"],
            "company": row["company"],
            "location": row["location"],
            "experience_level": row["experience_level"],
            "role_category": row["role_category"],
            "skills_text": row["skills_text"],
            "job_match_score": match_score,
            "matched_skills_count": len(matched_skills),
            "missing_skills_count": len(missing_skills),
            "matched_skills_preview": ", ".join(matched_skills[:5]) if matched_skills else "None",
            "missing_skills_preview": ", ".join(missing_skills[:5]) if missing_skills else "None",
        })

    job_match_df = pd.DataFrame(rows)

    if not job_match_df.empty:
        job_match_df = job_match_df.sort_values(
            by=["job_match_score", "matched_skills_count"],
            ascending=[False, False],
        )

    return job_match_df

def get_recommended_skills(
    jobs_df: pd.DataFrame,
    user_skills: list[str],
    role_skill_weights: dict,
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Recommend missing skills based on role importance and market demand.

    A skill ranks higher when:
    - it appears in more relevant jobs
    - it has a higher role-specific weight
    - the user does not already have it
    """

    if jobs_df.empty:
        return pd.DataFrame(
            columns=["skill", "score", "job_count", "avg_weight"]
        )

    user_skills_normalized = {
        skill.lower().strip()
        for skill in user_skills
    }

    skill_scores = {}

    for _, row in jobs_df.iterrows():
        role_category = row.get("role_category", "Other")
        category_weights = role_skill_weights.get(role_category, {})

        skills = row.get("extracted_skills", [])

        if isinstance(skills, str):
            skills = [
                skill.strip()
                for skill in skills.split(",")
                if skill.strip()
            ]

        for skill in skills:
            normalized_skill = skill.lower().strip()

            if not normalized_skill:
                continue

            if normalized_skill in user_skills_normalized:
                continue

            weight = category_weights.get(normalized_skill, 1)

            if normalized_skill not in skill_scores:
                skill_scores[normalized_skill] = {
                    "skill": skill,
                    "score": 0,
                    "job_count": 0,
                    "weight_total": 0,
                }

            skill_scores[normalized_skill]["score"] += weight
            skill_scores[normalized_skill]["job_count"] += 1
            skill_scores[normalized_skill]["weight_total"] += weight

    recommendations = []

    for item in skill_scores.values():
        item["avg_weight"] = item["weight_total"] / item["job_count"]
        recommendations.append(item)

    recommendations_df = pd.DataFrame(recommendations)

    if recommendations_df.empty:
        return pd.DataFrame(
            columns=["skill", "score", "job_count", "avg_weight"]
        )

    recommendations_df = recommendations_df.sort_values(
        by=["score", "job_count", "avg_weight"],
        ascending=False,
    ).head(top_n)

    return recommendations_df[
        ["skill", "score", "job_count", "avg_weight"]
    ]

def format_skills_for_sentence(skills: list[str], fallback: str) -> str:
    """Format a list of skills into a natural sentence fragment."""

    clean_skills = [
        skill
        for skill in skills
        if isinstance(skill, str) and skill.strip()
    ]

    if not clean_skills:
        return fallback

    if len(clean_skills) == 1:
        return clean_skills[0]

    if len(clean_skills) == 2:
        return f"{clean_skills[0]} and {clean_skills[1]}"

    return f"{', '.join(clean_skills[:-1])}, and {clean_skills[-1]}"


def get_candidate_fit_summary(
    filtered_jobs: pd.DataFrame,
    role_scores_df: pd.DataFrame,
    recommended_skills_df: pd.DataFrame,
) -> dict:
    """
    Build a natural-language candidate fit summary for the dashboard.
    """

    if filtered_jobs.empty:
        return {
            "summary": (
                "No matching postings were found for the current filters. "
                "Try broadening the role, location, or experience level filters."
            ),
            "matched_skills": [],
            "missing_skills": [],
        }

    if role_scores_df.empty:
        return {
            "summary": (
                "Matching postings were found, but there are not enough role scores "
                "available to generate a fit summary yet."
            ),
            "matched_skills": [],
            "missing_skills": [],
        }

    best_role_row = role_scores_df.sort_values(
        by="weighted_match_score",
        ascending=False,
    ).iloc[0]

    best_role = best_role_row["role_category"]
    best_score = best_role_row["weighted_match_score"]

    matched_skills = best_role_row.get("matched_skills", [])
    missing_skills = best_role_row.get("missing_skills", [])

    top_matched_skills = matched_skills[:4]

    if not recommended_skills_df.empty and "skill" in recommended_skills_df.columns:
        top_missing_skills = recommended_skills_df["skill"].head(3).tolist()
    else:
        top_missing_skills = missing_skills[:3]

    matched_text = format_skills_for_sentence(
        top_matched_skills,
        fallback="some relevant skills",
    )

    missing_text = format_skills_for_sentence(
        top_missing_skills,
        fallback="no major gaps from the current filters",
    )

    summary = (
        f"Based on <strong>{len(filtered_jobs)} matching postings</strong>, "
        f"your strongest fit is "
        f"<span class='summary-highlight'>{best_role}</span> "
        f"with a <strong>{best_score:.1f}% weighted match</strong>. "
        f"You already match <span class='summary-positive'>{matched_text}</span>. "
        f"Your highest-impact gaps are "
        f"<span class='summary-warning'>{missing_text}</span>."
    )

    return {
        "summary": summary,
        "matched_skills": top_matched_skills,
        "missing_skills": top_missing_skills,
    }

def get_role_sample_context(jobs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns how many job postings were analyzed per role category,
    plus a simple confidence label.
    """

    if jobs_df.empty:
        return pd.DataFrame(
            columns=["role_category", "job_count", "confidence"]
        )

    sample_context_df = (
        jobs_df.groupby("role_category")
        .size()
        .reset_index(name="job_count")
        .sort_values("job_count", ascending=False)
    )

    def confidence_label(job_count: int) -> str:
        if job_count >= 5:
            return "Strong sample"
        if job_count >= 3:
            return "Moderate sample"
        if job_count >= 1:
            return "Limited sample"
        return "No data"

    sample_context_df["confidence"] = sample_context_df["job_count"].apply(
        confidence_label
    )

    return sample_context_df