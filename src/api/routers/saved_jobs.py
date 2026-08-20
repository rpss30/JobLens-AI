from typing import Annotated

from fastapi import APIRouter, Query, status

from src.api.schemas import (
    DeleteSavedJobResponse,
    ErrorResponse,
    SavedJobResponse,
    SaveJobRequest,
)
from src.api.services import saved_job_service


router = APIRouter(
    prefix="/saved-jobs",
    tags=["saved-jobs"],
)


@router.get(
    "",
    response_model=list[SavedJobResponse],
    summary="List saved jobs",
    responses={503: {"model": ErrorResponse}},
)
def get_saved_jobs(
    dataset_name: Annotated[
        str | None,
        Query(max_length=255, description="Optional exact dataset name filter."),
    ] = None,
) -> list[SavedJobResponse]:
    return saved_job_service.list_kept_jobs(dataset_name)


@router.post(
    "",
    response_model=SavedJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a job",
    responses={503: {"model": ErrorResponse}},
)
def post_saved_job(request: SaveJobRequest) -> SavedJobResponse:
    return saved_job_service.keep_job(request)


@router.delete(
    "/{job_id}",
    response_model=DeleteSavedJobResponse,
    summary="Unsave a job",
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def delete_saved_job(
    job_id: str,
    dataset_name: Annotated[
        str,
        Query(max_length=255, description="Dataset the job belongs to."),
    ],
) -> DeleteSavedJobResponse:
    return saved_job_service.drop_kept_job(
        job_id=job_id,
        dataset_name=dataset_name,
    )
