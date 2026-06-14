from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException

from src.api.schemas import AnalyzeRequest, AnalyzeResponse
from src.dashboard.services import (
    filter_jobs,
    get_job_match_details,
    get_recommended_skills,
    prepare_processed_jobs_for_dashboard,
)
from src.matching.match_engine import build_role_skill_weights, score_roles
from src.processing.job_processor import process_jobs


RAW_DATA_PATH = "data/raw/sample_jobs.csv"
PROCESSED_DATA_PATH = "data/processed/processed_jobs.csv"

app = FastAPI(
    title="JobLens AI API",
    description="Backend API for JobLens AI role-fit and skill-gap analysis.",
    version="0.1.0",
)


@lru_cache(maxsize=1)
def load_api_jobs() -> pd.DataFrame:
    """
    Load the default JobLens dataset for API analysis.

    The API intentionally starts with the local sample dataset only.
    PostgreSQL and uploaded datasets can be added later without changing
    the core response contract.
    """
    jobs_df = process_jobs(
        input_path=RAW_DATA_PATH,
        output_path=PROCESSED_DATA_PATH,
    )

    return prepare_processed_jobs_for_dashboard(jobs_df)


def get_top_insights(
    role_scores_df: pd.DataFrame,
    recommended_skills_df: pd.DataFrame,
    filtered_jobs_df: pd.DataFrame,
) -> tuple[str, float, str, int]:
    """Return API-level fit summary metrics."""

    if role_scores_df.empty:
        return "No match", 0.0, "No skill gap", 0

    best_role_row = role_scores_df.sort_values(
        by="weighted_match_score",
        ascending=False,
    ).iloc[0]

    best_role = str(best_role_row["role_category"])
    best_score = float(best_role_row["weighted_match_score"])

    if recommended_skills_df.empty:
        top_missing_skill = "No major gaps"
    else:
        top_missing_skill = str(recommended_skills_df.iloc[0]["skill"])

    jobs_analyzed = len(filtered_jobs_df)

    return best_role, best_score, top_missing_skill, jobs_analyzed


def build_analyze_response(
    filtered_jobs: pd.DataFrame,
    current_skills: list[str],
    top_n: int,
) -> AnalyzeResponse:
    """Run matching and serialize dashboard analysis results for the API."""

    role_skill_weights = build_role_skill_weights(filtered_jobs)

    role_scores_df = score_roles(
        filtered_jobs,
        current_skills,
    )

    recommended_skills_df = get_recommended_skills(
        jobs_df=filtered_jobs,
        user_skills=current_skills,
        role_skill_weights=role_skill_weights,
        top_n=top_n,
    )

    job_match_details_df = get_job_match_details(
        filtered_jobs=filtered_jobs,
        user_skills=current_skills,
    )

    best_role, best_score, top_missing_skill, jobs_analyzed = get_top_insights(
        role_scores_df=role_scores_df,
        recommended_skills_df=recommended_skills_df,
        filtered_jobs_df=filtered_jobs,
    )

    recommended_skills = [
        {
            "skill": str(row["skill"]),
            "score": float(row["score"]),
            "job_count": int(row["job_count"]),
            "avg_weight": float(row["avg_weight"]),
        }
        for _, row in recommended_skills_df.head(top_n).iterrows()
    ]

    role_scores = [
        {
            "role_category": str(row["role_category"]),
            "sample_size": int(row["sample_size"]),
            "weighted_match_score": float(row["weighted_match_score"]),
            "unweighted_match_score": float(row["unweighted_match_score"]),
            "matched_weight": int(row["matched_weight"]),
            "total_possible_weight": int(row["total_possible_weight"]),
            "matched_skills": list(row["matched_skills"]),
            "missing_skills": list(row["missing_skills"]),
        }
        for _, row in role_scores_df.iterrows()
    ]

    top_matching_jobs = [
        {
            "title": str(row["title"]),
            "company": str(row["company"]),
            "location": str(row["location"]),
            "experience_level": str(row["experience_level"]),
            "role_category": str(row["role_category"]),
            "job_match_score": float(row["job_match_score"]),
            "matched_skills_count": int(row["matched_skills_count"]),
            "missing_skills_count": int(row["missing_skills_count"]),
            "matched_skills_preview": str(row["matched_skills_preview"]),
            "missing_skills_preview": str(row["missing_skills_preview"]),
        }
        for _, row in job_match_details_df.head(top_n).iterrows()
    ]

    return AnalyzeResponse(
        best_role=best_role,
        weighted_match_score=best_score,
        top_missing_skill=top_missing_skill,
        jobs_analyzed=jobs_analyzed,
        recommended_skills=recommended_skills,
        role_scores=role_scores,
        top_matching_jobs=top_matching_jobs,
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic API health check."""
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_jobs(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze candidate fit against the default JobLens dataset."""

    jobs_df = load_api_jobs()

    filtered_jobs = filter_jobs(
        df=jobs_df,
        target_roles=request.target_roles,
        location=request.location,
        experience_level=request.experience_level,
    )

    if filtered_jobs.empty:
        raise HTTPException(
            status_code=404,
            detail=(
                "No matching jobs found for the selected roles, location, "
                "and experience level."
            ),
        )

    return build_analyze_response(
        filtered_jobs=filtered_jobs,
        current_skills=request.current_skills,
        top_n=request.top_n,
    )