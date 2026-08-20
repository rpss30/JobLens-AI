from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from src.api.query_params import ListQueryParams, pagination_params
from src.api.schemas import ErrorResponse, JobDetail, JobListResponse
from src.api.services import job_listing_service
from src.api.services.job_listing_service import JobSortBy


router = APIRouter(tags=["jobs"])


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="Browse job postings in a dataset",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_jobs(
    query: Annotated[ListQueryParams, Depends(pagination_params)],
    dataset_name: Annotated[
        str | None,
        Query(
            max_length=120,
            description=(
                "Optional dataset name. Use 'canada_snapshot' for the bundled "
                "Canadian postings, a PostgreSQL dataset name, or omit for the "
                "local sample dataset."
            ),
        ),
    ] = None,
    target_roles: Annotated[
        list[str] | None,
        Query(description="Optional target job titles or role keywords."),
    ] = None,
    search_query: Annotated[
        str,
        Query(
            max_length=200,
            description="Optional free-text query used to rank postings.",
        ),
    ] = "",
    search_mode: Annotated[
        Literal["tfidf", "semantic", "hybrid"],
        Query(description="Search ranking mode."),
    ] = "tfidf",
    location: Annotated[
        str,
        Query(
            max_length=120,
            description="Location filter. Use 'Any' to disable location filtering.",
        ),
    ] = "Any",
    experience_level: Annotated[
        str,
        Query(
            max_length=80,
            description="Experience level filter. Use 'Any' to disable filtering.",
        ),
    ] = "Any",
    company: Annotated[
        str,
        Query(
            max_length=200,
            description=(
                "Employer filter, matched in full. Use 'Any' to disable it."
            ),
        ),
    ] = "Any",
    sort_by: Annotated[
        JobSortBy,
        Query(description="Job field to sort by."),
    ] = "search_relevance",
    saved_only: Annotated[
        bool,
        Query(description="Limit the listing to postings that have been saved."),
    ] = False,
) -> JobListResponse:
    return job_listing_service.list_jobs(
        dataset_name=dataset_name,
        target_roles=target_roles,
        search_query=search_query,
        search_mode=search_mode,
        location=location,
        experience_level=experience_level,
        company=company,
        sort_by=sort_by,
        sort_order=query.sort_order,
        limit=query.limit,
        offset=query.offset,
        saved_only=saved_only,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobDetail,
    summary="Read one job posting",
    responses={404: {"model": ErrorResponse}},
)
def get_job(
    job_id: str,
    dataset_name: Annotated[
        str | None,
        Query(max_length=120, description="Optional dataset name."),
    ] = None,
) -> JobDetail:
    return job_listing_service.get_job(dataset_name=dataset_name, job_id=job_id)
