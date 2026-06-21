# src/dashboard/services.py

import ast
import re
from html import escape
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.matching.match_engine import (
    RELATED_SKILL_THRESHOLD,
    build_role_skill_weights,
    build_skill_match_map,
    get_sample_confidence,
    normalize_skill,
    score_skill_set,
    select_best_role_row,
)
from src.processing.job_processor import process_jobs


RAW_DATA_PATH = "data/raw/sample_jobs.csv"
PROCESSED_DATA_PATH = "data/processed/processed_jobs.csv"
CANADA_JOBS_SNAPSHOT_PATH = "data/processed/canada_jobs_snapshot.csv"
GREENHOUSE_AI_DEMO_PATH = "data/processed/greenhouse_ai_demo_jobs.csv"


@st.cache_data
def load_processed_jobs() -> pd.DataFrame:
    """Load and process job data once."""
    jobs_df = process_jobs(
        input_path=RAW_DATA_PATH,
        output_path=PROCESSED_DATA_PATH,
    )

    return prepare_processed_jobs_for_dashboard(jobs_df)

def parse_extracted_skills_value(value: object) -> list[str]:
    """Parse extracted_skills values loaded from CSV into a clean list."""
    if isinstance(value, list):
        return [str(skill).strip() for skill in value if str(skill).strip()]

    if pd.isna(value):
        return []

    if not isinstance(value, str):
        return []

    stripped_value = value.strip()

    if not stripped_value:
        return []

    try:
        parsed_value = ast.literal_eval(stripped_value)
    except (ValueError, SyntaxError):
        parsed_value = None

    if isinstance(parsed_value, list):
        return [
            str(skill).strip()
            for skill in parsed_value
            if str(skill).strip()
        ]

    return [
        skill.strip()
        for skill in stripped_value.split(",")
        if skill.strip()
    ]


def prepare_processed_jobs_for_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize processed job dataframe columns for dashboard usage."""
    prepared_df = df.copy()

    if "extracted_skills" in prepared_df.columns:
        prepared_df["extracted_skills"] = prepared_df["extracted_skills"].apply(
            parse_extracted_skills_value
        )

    if "skills_text" not in prepared_df.columns and "extracted_skills" in prepared_df.columns:
        prepared_df["skills_text"] = prepared_df["extracted_skills"].apply(
            lambda skills: ", ".join(skills)
        )

    return prepared_df


@st.cache_data
def load_processed_jobs_from_csv(path: str) -> pd.DataFrame:
    """Load an already-processed jobs CSV for dashboard analysis."""
    csv_path = Path(path)

    if not csv_path.exists():
        return pd.DataFrame()

    loaded_df = pd.read_csv(csv_path)
    return prepare_processed_jobs_for_dashboard(loaded_df)

def read_uploaded_jobs_csv(uploaded_file) -> pd.DataFrame:
    """
    Read an uploaded jobs CSV using strict parsing so malformed rows
    are caught before validation.
    """

    return pd.read_csv(
        uploaded_file,
        engine="python",
        on_bad_lines="error",
    )
    
def validate_uploaded_jobs_csv(uploaded_df: pd.DataFrame) -> tuple[bool, str]:
    """
    Validate that an uploaded jobs CSV has the required structure
    for the JobLens AI processing pipeline.
    """

    required_columns = {
        "title",
        "company",
        "location",
        "description",
        "experience_level",
    }

    if uploaded_df.empty:
        return False, "Uploaded CSV is empty. Please upload a file with at least one job posting."

    missing_columns = required_columns - set(uploaded_df.columns)

    if missing_columns:
        return (
            False,
            "Uploaded CSV is missing required columns: "
            + ", ".join(sorted(missing_columns)),
        )

    required_null_counts = uploaded_df[list(required_columns)].isna().sum()
    columns_with_missing_values = required_null_counts[
        required_null_counts > 0
    ].index.tolist()

    if columns_with_missing_values:
        return (
            False,
            "Uploaded CSV has missing values in required columns: "
            + ", ".join(sorted(columns_with_missing_values)),
        )

    empty_text_columns = []

    for column in required_columns:
        has_empty_strings = (
            uploaded_df[column]
            .astype(str)
            .str.strip()
            .eq("")
            .any()
        )

        if has_empty_strings:
            empty_text_columns.append(column)

    if empty_text_columns:
        return (
            False,
            "Uploaded CSV has blank values in required columns: "
            + ", ".join(sorted(empty_text_columns)),
        )

    return True, "Uploaded CSV is valid."

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

            def has_term(term: str) -> bool:
                return bool(
                    re.search(
                        rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
                        clean_title,
                    )
                )

            generic_role_words = {
                "engineer",
                "developer",
                "analyst",
                "manager",
                "specialist",
                "principal",
                "staff",
            }

            cloud_role_terms = {
                "cloud",
                "aws",
                "devops",
                "platform",
                "infrastructure",
            }

            for role in role_keywords:
                role_words = role.split()
                role_cloud_terms = [
                    term for term in cloud_role_terms if term in role_words
                ]
                role_specific_non_cloud_words = [
                    word
                    for word in role_words
                    if word
                    not in {
                        "junior",
                        "senior",
                        "entry",
                        "level",
                        *generic_role_words,
                        *cloud_role_terms,
                    }
                ]

                # Full phrase match first.
                if role in clean_title:
                    return True

                # Role-family match for cloud/devops/platform roles.
                if (
                    role_cloud_terms
                    and not role_specific_non_cloud_words
                    and any(has_term(term) for term in role_cloud_terms)
                ):
                    return True

                # Flexible fallback, but ignore generic role words like "engineer".
                important_words = [
                    word
                    for word in role_words
                    if word
                    not in {
                        "junior",
                        "senior",
                        "entry",
                        "level",
                        *generic_role_words,
                    }
                ]

                if not important_words or not all(
                    has_term(word) for word in important_words
                ):
                    continue

                role_family_words = [
                    word for word in role_words if word in generic_role_words
                ]

                role_family_aliases = set(role_family_words)

                if "engineer" in role_family_words:
                    role_family_aliases.update({"developer", "architect"})
                if "developer" in role_family_words:
                    role_family_aliases.update({"engineer"})
                if "analyst" in role_family_words:
                    role_family_aliases.add("analytics")

                if role_family_aliases and not any(
                    has_term(word) for word in role_family_aliases
                ):
                    ai_or_ml_terms = {"ai", "ml", "machine", "learning"}

                    if not any(word in ai_or_ml_terms for word in important_words):
                        continue

                if important_words:
                    return True

            return False

        title_mask = filtered_df["clean_title"].apply(title_matches).astype(bool)

        filtered_df = filtered_df[title_mask]

        if filtered_df.empty:
            return filtered_df

    if location and location != "Any":
        location_lower = location.strip().lower()

        # "Toronto, ON" should still match "Toronto" or "Toronto ON"
        location_parts = [
            part.strip()
            for part in location_lower.replace(",", " ").split()
            if part.strip()
        ]

        location_mask = (
            filtered_df["location"]
            .astype(str)
            .str.lower()
            .apply(
                lambda job_location: any(
                    part in job_location
                    for part in location_parts
                )
            )
            .astype(bool)
        )

        filtered_df = filtered_df[location_mask]

        if filtered_df.empty:
            return filtered_df

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


def get_dataset_snapshot_summary(df: pd.DataFrame) -> dict[str, object]:
    """Return compact source metadata for a processed jobs snapshot."""
    if df.empty:
        return {
            "job_count": 0,
            "company_count": 0,
            "location_count": 0,
            "refreshed_date": "",
        }

    refreshed_date = ""

    if "fetched_at" in df.columns:
        fetched_dates = pd.to_datetime(
            df["fetched_at"],
            errors="coerce",
            utc=True,
        ).dropna()

        if not fetched_dates.empty:
            refreshed_date = fetched_dates.max().strftime("%B %d, %Y")

    return {
        "job_count": len(df),
        "company_count": (
            df["company"].dropna().nunique()
            if "company" in df.columns
            else 0
        ),
        "location_count": (
            df["location"].dropna().nunique()
            if "location" in df.columns
            else 0
        ),
        "refreshed_date": refreshed_date,
    }


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

def get_job_match_details(
    filtered_jobs: pd.DataFrame,
    user_skills: list[str],
) -> pd.DataFrame:
    """Build job-level match details for matching job postings."""
    role_skill_weights = build_role_skill_weights(filtered_jobs)
    all_required_skills = sorted({
        normalize_skill(skill)
        for skills in filtered_jobs.get("extracted_skills", pd.Series(dtype=object))
        if isinstance(skills, list)
        for skill in skills
        if normalize_skill(skill)
    })
    skill_match_map = build_skill_match_map(
        user_skills=user_skills,
        required_skills=all_required_skills,
    )

    rows = []

    for _, row in filtered_jobs.iterrows():
        job_skills_raw = row.get("extracted_skills", [])
        job_skills = []

        if isinstance(job_skills_raw, list):
            job_skills = job_skills_raw
        elif isinstance(job_skills_raw, str):
            job_skills = [skill.strip() for skill in job_skills_raw.split(",") if skill.strip()]

        role_category = str(row.get("role_category", "Other"))
        job_score = score_skill_set(
            required_skills=job_skills,
            role_category=role_category,
            role_skill_weights=role_skill_weights,
            skill_match_map=skill_match_map,
        )
        matched_skills = job_score["matched_skills"]
        related_skills = job_score["related_skills"]
        missing_skills = job_score["missing_skills"]

        rows.append({
            "title": row["title"],
            "company": row["company"],
            "location": row["location"],
            "experience_level": row["experience_level"],
            "role_category": role_category,
            "skills_text": row["skills_text"],
            "source": row.get("source", ""),
            "source_url": row.get("source_url", ""),
            "job_match_score": job_score["weighted_match_score"],
            "unweighted_job_match_score": job_score["unweighted_match_score"],
            "matched_skills_count": len(matched_skills),
            "related_skills_count": len(related_skills),
            "missing_skills_count": len(missing_skills),
            "matched_skills_preview": ", ".join(matched_skills[:5]) if matched_skills else "None",
            "related_skills_preview": ", ".join(related_skills[:3]) if related_skills else "None",
            "missing_skills_preview": ", ".join(missing_skills[:5]) if missing_skills else "None",
        })

    job_match_df = pd.DataFrame(rows)

    if not job_match_df.empty:
        job_match_df = job_match_df.sort_values(
            by=["job_match_score", "matched_skills_count"],
            ascending=[False, False],
        )

    return job_match_df

def get_positive_job_matches(job_match_details_df: pd.DataFrame) -> pd.DataFrame:
    """Return only job-level matches with positive skill overlap."""
    if (
        job_match_details_df.empty
        or "job_match_score" not in job_match_details_df.columns
    ):
        return job_match_details_df.copy()

    return job_match_details_df[
        job_match_details_df["job_match_score"] > 0
    ].copy()

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

    available_skills = sorted({
        normalize_skill(skill)
        for skills in jobs_df.get("extracted_skills", pd.Series(dtype=object))
        if isinstance(skills, list)
        for skill in skills
        if normalize_skill(skill)
    })
    skill_match_map = build_skill_match_map(
        user_skills=user_skills,
        required_skills=available_skills,
    )

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
            normalized_skill = normalize_skill(skill)

            if not normalized_skill:
                continue

            match_quality, _ = skill_match_map.get(
                normalized_skill,
                (0.0, None),
            )

            if match_quality >= RELATED_SKILL_THRESHOLD:
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

    best_role_row = select_best_role_row(role_scores_df)

    best_role = best_role_row["role_category"]
    best_score = float(best_role_row["weighted_match_score"])
    total_possible_weight = int(best_role_row.get("total_possible_weight", 0))

    matched_skills = best_role_row.get("matched_skills", [])
    missing_skills = best_role_row.get("missing_skills", [])
    representative_job_count = int(
        best_role_row.get("representative_job_count", 1)
    )
    sample_confidence = str(
        best_role_row.get("sample_confidence", "Limited")
    )

    top_matched_skills = matched_skills[:4]

    if missing_skills:
        top_missing_skills = missing_skills[:3]
    elif not recommended_skills_df.empty and "skill" in recommended_skills_df.columns:
        top_missing_skills = recommended_skills_df["skill"].head(3).tolist()
    else:
        top_missing_skills = []

    matched_text = format_skills_for_sentence(
        top_matched_skills,
        fallback="some relevant skills",
    )

    missing_text = format_skills_for_sentence(
        top_missing_skills,
        fallback="no major gaps from the current filters",
    )

    if best_score <= 0:
        if total_possible_weight == 0:
            summary = (
                f"Based on <strong>{len(filtered_jobs)} matching postings</strong>, "
                "JobLens could not calculate a meaningful skill-fit score because "
                "the selected postings do not have extracted skills yet. "
                "Try a broader filter or a dataset with richer skill extraction."
            )
        else:
            summary = (
                f"Based on <strong>{len(filtered_jobs)} matching postings</strong>, "
                "JobLens found <strong>no overlap</strong> between your current "
                f"skills and the extracted skills for "
                f"<span class='summary-highlight'>{best_role}</span>. "
                f"The highest-impact gaps are "
                f"<span class='summary-warning'>{missing_text}</span>."
            )

        return {
            "summary": summary,
            "matched_skills": [],
            "missing_skills": top_missing_skills,
        }

    summary = (
        f"Based on <strong>{len(filtered_jobs)} matching postings</strong>, "
        f"your strongest fit is "
        f"<span class='summary-highlight'>{best_role}</span> "
        f"with a <strong>{best_score:.1f}% role skill fit</strong>, based on "
        f"<strong>{representative_job_count} representative "
        f"{'posting' if representative_job_count == 1 else 'postings'}</strong> "
        f"with {sample_confidence.lower()} sample confidence. "
        f"You already match <span class='summary-positive'>{matched_text}</span>. "
        f"Your highest-impact gaps are "
        f"<span class='summary-warning'>{missing_text}</span>."
    )

    return {
        "summary": summary,
        "matched_skills": top_matched_skills,
        "missing_skills": top_missing_skills,
    }

def generate_candidate_report_markdown(
    current_skills: list[str],
    target_roles: list[str],
    location: str,
    experience_level: str,
    filtered_jobs: pd.DataFrame,
    role_scores_df: pd.DataFrame,
    recommended_skills_df: pd.DataFrame,
    job_match_details_df: pd.DataFrame,
    candidate_fit_summary: dict | None = None,
    dataset_name: str = "Current dataset",
) -> str:
    """
    Generate a downloadable Markdown candidate skill-gap report.

    This function only formats already-computed dashboard results.
    It does not perform scoring, filtering, or recommendation logic.
    """

    def clean_html(raw_text: object) -> str:
        if not isinstance(raw_text, str):
            return ""

        return re.sub(r"<[^>]+>", "", raw_text).strip()

    def format_list(values: list[str], fallback: str = "None selected") -> str:
        clean_values = [
            str(value).strip()
            for value in values
            if str(value).strip()
        ]

        if not clean_values:
            return fallback

        return ", ".join(clean_values)

    def format_skill_list(value: object, fallback: str = "None") -> str:
        if isinstance(value, list):
            return format_list(value, fallback=fallback)

        if isinstance(value, str) and value.strip():
            return value.strip()

        return fallback

    jobs_analyzed = len(filtered_jobs)

    best_role = "N/A"
    best_score = 0.0
    top_missing_skill = "N/A"
    representative_job_count = 0
    sample_confidence = "Insufficient"

    if not role_scores_df.empty and "weighted_match_score" in role_scores_df.columns:
        best_role_row = select_best_role_row(role_scores_df)

        best_role = str(best_role_row.get("role_category", "N/A"))
        best_score = float(best_role_row.get("weighted_match_score", 0.0))
        representative_job_count = int(
            best_role_row.get("representative_job_count", 0)
        )
        sample_confidence = str(
            best_role_row.get("sample_confidence", "Insufficient")
        )

        missing_skills = best_role_row.get("missing_skills", [])
        if isinstance(missing_skills, list) and missing_skills:
            top_missing_skill = str(missing_skills[0])

    if (
        top_missing_skill == "N/A"
        and not recommended_skills_df.empty
        and "skill" in recommended_skills_df.columns
    ):
        top_missing_skill = str(recommended_skills_df.iloc[0]["skill"])

    report_lines = [
        "# JobLens AI Candidate Skill-Gap Report",
        "",
        "## Analysis Inputs",
        "",
        f"- Dataset: {dataset_name}",
        f"- Target roles: {format_list(target_roles)}",
        f"- Location filter: {location or 'Any'}",
        f"- Experience level filter: {experience_level or 'Any'}",
        f"- Current skills: {format_list(current_skills)}",
        "",
        "## Fit Overview",
        "",
        f"- Jobs analyzed: {jobs_analyzed}",
        f"- Best-fit role category: {best_role}",
        f"- Role skill fit: {best_score:.1f}%",
        f"- Representative postings: {representative_job_count}",
        f"- Sample confidence: {sample_confidence}",
        f"- Top recommended skill gap: {top_missing_skill}",
        "",
    ]

    if candidate_fit_summary and candidate_fit_summary.get("summary"):
        report_lines.extend([
            "## Candidate Fit Summary",
            "",
            clean_html(candidate_fit_summary["summary"]),
            "",
        ])

    report_lines.extend([
        "## Recommended Skills to Learn",
        "",
    ])

    if recommended_skills_df.empty:
        report_lines.append("No recommended skills were generated for the current filters.")
    else:
        report_lines.extend([
            "| Skill | Score | Job Count | Average Weight |",
            "| --- | ---: | ---: | ---: |",
        ])

        for _, row in recommended_skills_df.head(10).iterrows():
            report_lines.append(
                "| "
                f"{row.get('skill', 'N/A')} | "
                f"{float(row.get('score', 0)):.2f} | "
                f"{int(row.get('job_count', 0))} | "
                f"{float(row.get('avg_weight', 0)):.2f} |"
            )

    report_lines.extend([
        "",
        "## Role Score Breakdown",
        "",
    ])

    if role_scores_df.empty:
        report_lines.append("No role score breakdown is available for the current filters.")
    else:
        report_lines.extend([
            "| Role Category | Role Skill Fit | Confidence | Representative Jobs | Matched Skills | Missing Skills |",
            "| --- | ---: | --- | ---: | --- | --- |",
        ])

        sorted_role_scores = role_scores_df.sort_values(
            by="weighted_match_score",
            ascending=False,
        )

        for _, row in sorted_role_scores.iterrows():
            report_lines.append(
                "| "
                f"{row.get('role_category', 'N/A')} | "
                f"{float(row.get('weighted_match_score', 0)):.1f}% | "
                f"{row.get('sample_confidence', 'N/A')} | "
                f"{int(row.get('representative_job_count', 0))} | "
                f"{format_skill_list(row.get('matched_skills', []))} | "
                f"{format_skill_list(row.get('missing_skills', []))} |"
            )

    report_lines.extend([
        "",
        "## Top Matching Jobs",
        "",
    ])

    positive_job_matches_df = get_positive_job_matches(job_match_details_df)

    if positive_job_matches_df.empty:
        report_lines.append(
            "No positive job-level matches are available for the current filters."
        )
    else:
        report_lines.extend([
            "| Title | Company | Location | Match Score | Matched Skills | Missing Skills |",
            "| --- | --- | --- | ---: | --- | --- |",
        ])

        for _, row in positive_job_matches_df.head(10).iterrows():
            report_lines.append(
                "| "
                f"{row.get('title', 'N/A')} | "
                f"{row.get('company', 'N/A')} | "
                f"{row.get('location', 'N/A')} | "
                f"{float(row.get('job_match_score', 0)):.1f}% | "
                f"{row.get('matched_skills_preview', 'None')} | "
                f"{row.get('missing_skills_preview', 'None')} |"
            )

    report_lines.extend([
        "",
        "## Notes",
        "",
        (
            "This report is based on the currently selected JobLens AI dataset, "
            "filters, and candidate skills. Match scores are intended for portfolio "
            "analysis and skill-gap exploration, not hiring decisions."
        ),
        "",
    ])

    return "\n".join(report_lines)


def generate_candidate_report_pdf(
    current_skills: list[str],
    target_roles: list[str],
    location: str,
    experience_level: str,
    filtered_jobs: pd.DataFrame,
    role_scores_df: pd.DataFrame,
    recommended_skills_df: pd.DataFrame,
    job_match_details_df: pd.DataFrame,
    candidate_fit_summary: dict | None = None,
    dataset_name: str = "Current dataset",
) -> bytes:
    """
    Generate a downloadable PDF candidate skill-gap report.

    This mirrors the Markdown report content while using a structured PDF
    layout suitable for sharing as a portfolio/demo artifact.
    """

    def clean_html(raw_text: object) -> str:
        if not isinstance(raw_text, str):
            return ""

        return re.sub(r"<[^>]+>", "", raw_text).strip()

    def format_list(values: list[str], fallback: str = "None selected") -> str:
        clean_values = [
            str(value).strip()
            for value in values
            if str(value).strip()
        ]

        if not clean_values:
            return fallback

        return ", ".join(clean_values)

    def format_skill_list(value: object, fallback: str = "None") -> str:
        if isinstance(value, list):
            return format_list(value, fallback=fallback)

        if isinstance(value, str) and value.strip():
            return value.strip()

        return fallback

    def paragraph(text: object, style: ParagraphStyle) -> Paragraph:
        return Paragraph(escape(str(text)), style)

    def section_title(text: str) -> None:
        story.append(Spacer(1, 0.16 * inch))
        story.append(paragraph(text, styles["ReportHeading"]))
        story.append(Spacer(1, 0.06 * inch))

    def build_table(
        headers: list[str],
        rows: list[list[object]],
        column_widths: list[float],
    ) -> Table:
        table_data = [
            [paragraph(header, styles["TableHeader"]) for header in headers]
        ]

        for row in rows:
            table_data.append([
                paragraph(value, styles["TableCell"])
                for value in row
            ])

        table = Table(
            table_data,
            colWidths=column_widths,
            hAlign="LEFT",
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("BOX", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table

    def add_footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(doc.leftMargin, 0.42 * inch, "JobLens AI")
        canvas.drawRightString(
            letter[0] - doc.rightMargin,
            0.42 * inch,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    jobs_analyzed = len(filtered_jobs)

    best_role = "N/A"
    best_score = 0.0
    top_missing_skill = "N/A"
    representative_job_count = 0
    sample_confidence = "Insufficient"

    if not role_scores_df.empty and "weighted_match_score" in role_scores_df.columns:
        best_role_row = select_best_role_row(role_scores_df)

        best_role = str(best_role_row.get("role_category", "N/A"))
        best_score = float(best_role_row.get("weighted_match_score", 0.0))
        representative_job_count = int(
            best_role_row.get("representative_job_count", 0)
        )
        sample_confidence = str(
            best_role_row.get("sample_confidence", "Insufficient")
        )

        missing_skills = best_role_row.get("missing_skills", [])
        if isinstance(missing_skills, list) and missing_skills:
            top_missing_skill = str(missing_skills[0])

    if (
        top_missing_skill == "N/A"
        and not recommended_skills_df.empty
        and "skill" in recommended_skills_df.columns
    ):
        top_missing_skill = str(recommended_skills_df.iloc[0]["skill"])

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.6 * inch,
        title="JobLens AI Candidate Skill-Gap Report",
    )

    stylesheet = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "ReportTitle",
            parent=stylesheet["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=8,
        ),
        "Subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=stylesheet["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        ),
        "ReportHeading": ParagraphStyle(
            "ReportHeading",
            parent=stylesheet["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=4,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "ReportBody",
            parent=stylesheet["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
        ),
        "TableHeader": ParagraphStyle(
            "ReportTableHeader",
            parent=stylesheet["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.2,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        ),
        "TableCell": ParagraphStyle(
            "ReportTableCell",
            parent=stylesheet["BodyText"],
            fontName="Helvetica",
            fontSize=7.7,
            leading=9.5,
            textColor=colors.HexColor("#1e293b"),
        ),
    }

    story: list = [
        paragraph("JobLens AI Candidate Skill-Gap Report", styles["Title"]),
        paragraph(
            "Personalized job market intelligence for role fit, skill gaps, "
            "and learning priorities.",
            styles["Subtitle"],
        ),
    ]

    section_title("Analysis Inputs")
    story.append(
        build_table(
            headers=["Field", "Value"],
            rows=[
                ["Dataset", dataset_name],
                ["Target roles", format_list(target_roles)],
                ["Location filter", location or "Any"],
                ["Experience level filter", experience_level or "Any"],
                ["Current skills", format_list(current_skills)],
            ],
            column_widths=[1.65 * inch, 5.65 * inch],
        )
    )

    section_title("Fit Overview")
    story.append(
        build_table(
            headers=["Metric", "Value"],
            rows=[
                ["Jobs analyzed", jobs_analyzed],
                ["Best-fit role category", best_role],
                ["Role skill fit", f"{best_score:.1f}%"],
                ["Representative postings", representative_job_count],
                ["Sample confidence", sample_confidence],
                ["Top recommended skill gap", top_missing_skill],
            ],
            column_widths=[2.1 * inch, 5.2 * inch],
        )
    )

    if candidate_fit_summary and candidate_fit_summary.get("summary"):
        section_title("Candidate Fit Summary")
        story.append(
            paragraph(
                clean_html(candidate_fit_summary["summary"]),
                styles["Body"],
            )
        )

    section_title("Recommended Skills to Learn")
    if recommended_skills_df.empty:
        story.append(
            paragraph(
                "No recommended skills were generated for the current filters.",
                styles["Body"],
            )
        )
    else:
        recommended_rows = []
        for _, row in recommended_skills_df.head(10).iterrows():
            recommended_rows.append([
                row.get("skill", "N/A"),
                f"{float(row.get('score', 0)):.2f}",
                int(row.get("job_count", 0)),
                f"{float(row.get('avg_weight', 0)):.2f}",
            ])

        story.append(
            build_table(
                headers=["Skill", "Score", "Job Count", "Average Weight"],
                rows=recommended_rows,
                column_widths=[
                    2.5 * inch,
                    1.1 * inch,
                    1.3 * inch,
                    1.5 * inch,
                ],
            )
        )

    section_title("Role Score Breakdown")
    if role_scores_df.empty:
        story.append(
            paragraph(
                "No role score breakdown is available for the current filters.",
                styles["Body"],
            )
        )
    else:
        sorted_role_scores = role_scores_df.sort_values(
            by="weighted_match_score",
            ascending=False,
        )
        role_rows = []
        for _, row in sorted_role_scores.iterrows():
            role_rows.append([
                row.get("role_category", "N/A"),
                f"{float(row.get('weighted_match_score', 0)):.1f}%",
                row.get("sample_confidence", "N/A"),
                int(row.get("representative_job_count", 0)),
                format_skill_list(row.get("matched_skills", [])),
                format_skill_list(row.get("missing_skills", [])),
            ])

        story.append(
            build_table(
                headers=[
                    "Role Category",
                    "Role Skill Fit",
                    "Confidence",
                    "Rep. Jobs",
                    "Matched Skills",
                    "Missing Skills",
                ],
                rows=role_rows,
                column_widths=[
                    1.2 * inch,
                    0.75 * inch,
                    0.7 * inch,
                    0.55 * inch,
                    1.8 * inch,
                    2.2 * inch,
                ],
            )
        )

    section_title("Top Matching Jobs")
    positive_job_matches_df = get_positive_job_matches(job_match_details_df)

    if positive_job_matches_df.empty:
        story.append(
            paragraph(
                "No positive job-level matches are available for the current filters.",
                styles["Body"],
            )
        )
    else:
        top_job_rows = []
        for _, row in positive_job_matches_df.head(10).iterrows():
            top_job_rows.append([
                row.get("title", "N/A"),
                row.get("company", "N/A"),
                f"{float(row.get('job_match_score', 0)):.1f}%",
                row.get("matched_skills_preview", "None"),
            ])

        story.append(
            build_table(
                headers=["Title", "Company", "Match", "Matched Skills"],
                rows=top_job_rows,
                column_widths=[
                    2.55 * inch,
                    1.45 * inch,
                    0.75 * inch,
                    2.45 * inch,
                ],
            )
        )

    section_title("Notes")
    story.append(
        paragraph(
            "This report is based on the currently selected JobLens AI dataset, "
            "filters, and candidate skills. Match scores are intended for "
            "portfolio analysis and skill-gap exploration, not hiring decisions.",
            styles["Body"],
        )
    )

    document.build(story, onFirstPage=add_footer, onLaterPages=add_footer)

    return buffer.getvalue()


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

    sample_context_df["confidence"] = sample_context_df["job_count"].apply(
        lambda job_count: get_sample_confidence(job_count)[1]
    )

    return sample_context_df
