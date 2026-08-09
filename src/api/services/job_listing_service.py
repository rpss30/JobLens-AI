from typing import Literal

import pandas as pd

from src.api.schemas import JobListResponse
from src.api.services.analysis_service import clean_optional_text, load_jobs_for_analysis
from src.api.services.listing import paginate_items, sort_items
from src.dashboard.services import filter_jobs


JobSortBy = Literal[
    "search_relevance",
    "title",
    "company",
    "location",
    "date_posted",
]


def clean_optional_flag(value: object) -> bool:
    """Return a boolean for optional posting flags stored as text or numbers."""
    if isinstance(value, bool):
        return value

    return clean_optional_text(value).lower() in {"true", "yes", "1"}


def build_job_listing_row(row: pd.Series) -> dict:
    """Map one processed job posting to its browse-friendly listing fields."""
    skills = row.get("extracted_skills", [])

    if not isinstance(skills, list):
        skills = []

    return {
        "job_id": clean_optional_text(row.get("job_id", "")),
        "title": clean_optional_text(row.get("title", "")),
        "company": clean_optional_text(row.get("company", "")),
        "location": clean_optional_text(row.get("location", "")),
        "experience_level": clean_optional_text(row.get("experience_level", "")),
        "role_category": clean_optional_text(row.get("role_category", "")),
        "employment_type": clean_optional_text(row.get("employment_type", "")),
        "workplace_type": clean_optional_text(row.get("workplace_type", "")),
        "is_remote": clean_optional_flag(row.get("is_remote", False)),
        "date_posted": clean_optional_text(row.get("date_posted", "")),
        "source": clean_optional_text(row.get("source", "")),
        "source_url": clean_optional_text(row.get("source_url", "")),
        "skills": [str(skill).strip() for skill in skills if str(skill).strip()],
        "search_relevance": float(row.get("search_relevance", 0.0) or 0.0),
    }


def list_jobs(
    *,
    dataset_name: str | None = None,
    target_roles: list[str] | None = None,
    search_query: str = "",
    search_mode: str = "tfidf",
    location: str = "Any",
    experience_level: str = "Any",
    sort_by: JobSortBy = "search_relevance",
    sort_order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> JobListResponse:
    """Return a filtered, sorted, and paginated slice of job postings."""
    resolved_dataset_name, jobs_df = load_jobs_for_analysis(dataset_name)

    filtered_jobs = filter_jobs(
        df=jobs_df,
        target_roles=target_roles or [],
        location=location,
        experience_level=experience_level,
        search_query=search_query,
        search_mode=search_mode,
    )

    jobs = [build_job_listing_row(row) for _, row in filtered_jobs.iterrows()]
    jobs = sort_items(jobs, sort_by=sort_by, sort_order=sort_order)

    return JobListResponse(
        dataset_name=resolved_dataset_name,
        total=len(jobs),
        limit=limit,
        offset=offset,
        jobs=paginate_items(jobs, limit=limit, offset=offset),
    )
