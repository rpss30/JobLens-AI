from functools import lru_cache

import pandas as pd

from src.api.errors import ApiError
from src.api.schemas import AnalyzeRequest, AnalyzeResponse
from src.dashboard.services import (
    filter_jobs,
    get_job_match_details,
    get_positive_job_matches,
    get_recommended_skills,
    prepare_processed_jobs_for_dashboard,
)
from src.database import repository as database_repository
from src.matching.match_engine import (
    build_role_skill_weights,
    score_roles,
    select_best_role_row,
)
from src.processing.job_processor import process_jobs
from src.resume.resume_analyzer import analyze_resume_against_jobs


RAW_DATA_PATH = "data/raw/sample_jobs.csv"
PROCESSED_DATA_PATH = "data/processed/processed_jobs.csv"
LOCAL_SAMPLE_DATASET_NAME = "local_sample"


@lru_cache(maxsize=1)
def load_api_jobs() -> pd.DataFrame:
    """Load the local sample JobLens dataset for API analysis."""
    jobs_df = process_jobs(
        input_path=RAW_DATA_PATH,
        output_path=PROCESSED_DATA_PATH,
    )

    return prepare_processed_jobs_for_dashboard(jobs_df)


def load_jobs_for_analysis(dataset_name: str | None) -> tuple[str, pd.DataFrame]:
    if not dataset_name:
        return LOCAL_SAMPLE_DATASET_NAME, load_api_jobs()

    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so database datasets cannot be loaded.",
        )

    try:
        jobs_df = database_repository.load_processed_jobs_dataframe(
            dataset_name=dataset_name
        )
    except Exception as error:
        raise ApiError(
            status_code=500,
            detail=f"Could not load dataset '{dataset_name}' from PostgreSQL.",
        ) from error

    if jobs_df.empty:
        raise ApiError(
            status_code=404,
            detail=f"Dataset '{dataset_name}' was not found or contains no processed jobs.",
        )

    return dataset_name, prepare_processed_jobs_for_dashboard(jobs_df)


def get_top_insights(
    role_scores_df: pd.DataFrame,
    recommended_skills_df: pd.DataFrame,
    filtered_jobs_df: pd.DataFrame,
) -> tuple[str, float, str, int]:
    if role_scores_df.empty:
        return "No match", 0.0, "No skill gap", 0

    best_role_row = select_best_role_row(role_scores_df)

    best_role = str(best_role_row["role_category"])
    best_score = float(best_role_row["weighted_match_score"])

    if best_score <= 0:
        total_possible_weight = int(best_role_row.get("total_possible_weight", 0))
        best_role = (
            "No skill overlap"
            if total_possible_weight > 0
            else "Insufficient skill data"
        )

    missing_skills = best_role_row.get("missing_skills", [])

    if isinstance(missing_skills, list) and missing_skills:
        top_missing_skill = str(missing_skills[0])
    elif not recommended_skills_df.empty:
        top_missing_skill = str(recommended_skills_df.iloc[0]["skill"])
    else:
        top_missing_skill = "No major gaps"

    jobs_analyzed = len(filtered_jobs_df)

    return best_role, best_score, top_missing_skill, jobs_analyzed


def build_analyze_response(
    *,
    dataset_name: str,
    filtered_jobs: pd.DataFrame,
    current_skills: list[str],
    resume_text: str = "",
    target_roles: list[str] | None = None,
    top_n: int,
) -> AnalyzeResponse:
    resume_analysis = None
    analysis_skills = current_skills

    if resume_text.strip():
        resume_analysis = analyze_resume_against_jobs(
            jobs_df=filtered_jobs,
            resume_text=resume_text,
            current_skills=current_skills,
            target_roles=target_roles or [],
        )
        analysis_skills = list(resume_analysis["combined_skills"])

    role_skill_weights = build_role_skill_weights(filtered_jobs)

    role_scores_df = score_roles(
        filtered_jobs,
        analysis_skills,
    )

    recommended_skills_df = get_recommended_skills(
        jobs_df=filtered_jobs,
        user_skills=analysis_skills,
        role_skill_weights=role_skill_weights,
        top_n=top_n,
    )

    job_match_details_df = get_job_match_details(
        filtered_jobs=filtered_jobs,
        user_skills=analysis_skills,
    )
    positive_job_matches_df = get_positive_job_matches(job_match_details_df)

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
            "matched_weight": float(row["matched_weight"]),
            "total_possible_weight": float(row["total_possible_weight"]),
            "matched_skills": list(row["matched_skills"]),
            "related_skills": list(row["related_skills"]),
            "missing_skills": list(row["missing_skills"]),
            "representative_job_count": int(row["representative_job_count"]),
            "sample_confidence": str(row["sample_confidence"]),
            "headline_eligible": bool(row["headline_eligible"]),
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
            "search_relevance": float(row["search_relevance"]),
            "semantic_relevance": float(row.get("semantic_relevance", 0.0)),
            "tfidf_relevance": float(row.get("tfidf_relevance", 0.0)),
            "search_mode": str(row.get("search_mode", "tfidf")),
            "job_match_score": float(row["job_match_score"]),
            "matched_skills_count": int(row["matched_skills_count"]),
            "related_skills_count": int(row["related_skills_count"]),
            "missing_skills_count": int(row["missing_skills_count"]),
            "matched_skills_preview": str(row["matched_skills_preview"]),
            "related_skills_preview": str(row["related_skills_preview"]),
            "missing_skills_preview": str(row["missing_skills_preview"]),
        }
        for _, row in positive_job_matches_df.head(top_n).iterrows()
    ]

    return AnalyzeResponse(
        dataset_name=dataset_name,
        best_role=best_role,
        weighted_match_score=best_score,
        top_missing_skill=top_missing_skill,
        jobs_analyzed=jobs_analyzed,
        recommended_skills=recommended_skills,
        role_scores=role_scores,
        top_matching_jobs=top_matching_jobs,
        resume_analysis=resume_analysis,
    )


def analyze_jobs(request: AnalyzeRequest) -> AnalyzeResponse:
    dataset_name, jobs_df = load_jobs_for_analysis(request.dataset_name)

    filtered_jobs = filter_jobs(
        df=jobs_df,
        target_roles=request.target_roles,
        location=request.location,
        experience_level=request.experience_level,
        search_query=request.search_query,
        search_mode=request.search_mode,
    )

    if filtered_jobs.empty:
        raise ApiError(
            status_code=404,
            detail=(
                "No matching jobs found for the search query and selected "
                "role, location, or experience filters."
            ),
        )

    return build_analyze_response(
        dataset_name=dataset_name,
        filtered_jobs=filtered_jobs,
        current_skills=request.current_skills,
        resume_text=request.resume_text,
        target_roles=request.target_roles,
        top_n=request.top_n,
    )
