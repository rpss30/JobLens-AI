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
    """Filter jobs based on user input."""
    filtered_df = df.copy()

    if target_roles:
        role_keywords = [
            role.strip().lower()
            for role in target_roles
            if role.strip()
        ]

        filtered_df = filtered_df[
            filtered_df["clean_title"].apply(
                lambda title: any(keyword in title for keyword in role_keywords)
            )
        ]

    if location:
        location_lower = location.strip().lower()
        filtered_df = filtered_df[
            filtered_df["location"].str.lower().str.contains(location_lower, na=False)
        ]

    if experience_level and experience_level != "Any":
        filtered_df = filtered_df[
            filtered_df["experience_level"].str.lower()
            == experience_level.lower()
        ]

    return filtered_df


def get_top_companies(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Return companies with the most matching jobs."""
    company_counts = df["company"].value_counts().head(top_n)

    return pd.DataFrame({
        "company": company_counts.index,
        "job_count": company_counts.values,
    })


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