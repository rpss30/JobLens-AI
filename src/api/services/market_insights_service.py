import pandas as pd

from src.api.errors import ApiError
from src.api.schemas import MarketInsightsRequest, MarketInsightsResponse
from src.api.services.analysis_service import load_jobs_for_analysis
from src.analysis.job_services import (
    filter_jobs,
    get_jobs_by_location,
    get_top_companies,
)
from src.matching.match_engine import (
    build_role_skill_weights,
    get_role_weighted_top_skills,
    get_top_skills,
)
from src.matching.skill_requirements import summarize_skill_requirement
from src.skill_extraction.normalizer import normalize_skill_key


# Rank within a role, not a share of its postings. Role categories are broad
# and fragmented, so even a defining skill rarely reaches half the postings in
# its own category; what matters is where it sits against its peers.
LEADING_SIGNAL_RANK = 3
COMMON_SIGNAL_RANK = 6


def describe_demand_signal(rank: int) -> str:
    if rank <= LEADING_SIGNAL_RANK:
        return "leading"

    if rank <= COMMON_SIGNAL_RANK:
        return "common"

    return "specialized"


def build_role_skill_rows(
    jobs_df: pd.DataFrame,
    role_skill_importance_df: pd.DataFrame,
) -> list[dict]:
    """Turn internal weights into evidence a reader can check.

    Each row carries the counts behind its labels, so the page can say "12 of
    29 Software Engineering postings" rather than asking anyone to trust a
    weighting formula they cannot see.
    """
    rows: list[dict] = []
    rank_by_role: dict[str, int] = {}

    for _, row in role_skill_importance_df.iterrows():
        role_category = str(row["role_category"])
        skill = str(row["skill"])
        rank = rank_by_role.get(role_category, 0) + 1
        rank_by_role[role_category] = rank

        role_jobs = jobs_df[jobs_df["role_category"] == role_category]
        skill_key = normalize_skill_key(skill)
        descriptions = [
            job_row.get("description")
            for _, job_row in role_jobs.iterrows()
            if any(
                normalize_skill_key(str(entry)) == skill_key
                for entry in (job_row.get("extracted_skills") or [])
            )
        ]

        rows.append(
            {
                "role_category": role_category,
                "skill": skill,
                "job_count": int(row["count"]),
                "role_job_count": int(len(role_jobs)),
                "role_weight": int(row["role_weight"]),
                "weighted_importance": float(row["weighted_importance"]),
                "demand_signal": describe_demand_signal(rank),
                **summarize_skill_requirement(skill, descriptions),
            }
        )

    return rows


def get_role_distribution(jobs_df: pd.DataFrame, top_n: int) -> list[dict]:
    """Return matching posting counts grouped by role category."""
    if jobs_df.empty or "role_category" not in jobs_df.columns:
        return []

    role_counts = jobs_df["role_category"].value_counts().head(top_n)

    return [
        {
            "role_category": str(role_category),
            "job_count": int(job_count),
        }
        for role_category, job_count in role_counts.items()
    ]


def get_market_insights(request: MarketInsightsRequest) -> MarketInsightsResponse:
    """Return market-level skill, location, and employer demand for a job slice."""
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

    role_skill_weights = build_role_skill_weights(filtered_jobs)

    top_skills_df = get_top_skills(filtered_jobs, top_n=request.top_n)
    role_skill_importance_df = get_role_weighted_top_skills(
        filtered_jobs,
        role_skill_weights,
        top_n=request.top_n,
        # Per role, or the busiest category crowds every other one out.
        per_role=True,
    )
    jobs_by_location_df = get_jobs_by_location(filtered_jobs).head(request.top_n)
    top_companies_df = get_top_companies(filtered_jobs, top_n=request.top_n)

    return MarketInsightsResponse(
        dataset_name=dataset_name,
        jobs_analyzed=len(filtered_jobs),
        skill_demand=[
            {
                "skill": str(row["skill"]),
                "job_count": int(row["count"]),
            }
            for _, row in top_skills_df.iterrows()
        ],
        role_skill_importance=build_role_skill_rows(
            filtered_jobs,
            role_skill_importance_df,
        ),
        jobs_by_location=[
            {
                "location": str(row["location"]),
                "job_count": int(row["job_count"]),
            }
            for _, row in jobs_by_location_df.iterrows()
        ],
        top_companies=[
            {
                "company": str(row["company"]),
                "job_count": int(row["job_count"]),
            }
            for _, row in top_companies_df.iterrows()
        ],
        role_distribution=get_role_distribution(filtered_jobs, request.top_n),
    )
