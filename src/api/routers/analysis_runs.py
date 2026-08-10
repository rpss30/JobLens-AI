from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.query_params import ListQueryParams, pagination_params
from src.api.schemas import (
    AnalysisRunResponse,
    CreateAnalysisRunRequest,
    DeleteAnalysisRunResponse,
    ErrorResponse,
    RenameAnalysisRunRequest,
    RenameAnalysisRunResponse,
)
from src.api.services import analysis_run_service
from src.api.services.analysis_run_service import AnalysisRunSortBy


router = APIRouter(
    prefix="/analysis-runs",
    tags=["analysis-runs"],
)


@router.get(
    "",
    response_model=list[AnalysisRunResponse],
    summary="List saved analysis runs",
    responses={503: {"model": ErrorResponse}},
)
def get_analysis_runs(
    query: Annotated[ListQueryParams, Depends(pagination_params)],
    dataset_name: Annotated[
        str | None,
        Query(
            max_length=255,
            description="Optional exact dataset name filter.",
        ),
    ] = None,
    sort_by: Annotated[
        AnalysisRunSortBy,
        Query(description="Analysis run field to sort by."),
    ] = "created_at",
) -> list[dict]:
    return analysis_run_service.list_saved_analysis_runs(
        dataset_name=dataset_name,
        sort_by=sort_by,
        sort_order=query.sort_order,
        limit=query.limit,
        offset=query.offset,
    )


@router.post(
    "",
    response_model=AnalysisRunResponse,
    status_code=201,
    summary="Save an analysis run",
    responses={
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def create_analysis_run(request: CreateAnalysisRunRequest) -> dict:
    return analysis_run_service.create_analysis_run(request)


@router.get(
    "/{analysis_run_id}",
    response_model=AnalysisRunResponse,
    summary="Load one saved analysis run",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_analysis_run(analysis_run_id: int) -> dict:
    return analysis_run_service.get_saved_analysis_run(analysis_run_id)


@router.patch(
    "/{analysis_run_id}",
    response_model=RenameAnalysisRunResponse,
    summary="Rename a saved analysis run",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def rename_analysis_run(
    analysis_run_id: int,
    request: RenameAnalysisRunRequest,
) -> dict:
    return analysis_run_service.rename_saved_analysis_run(
        analysis_run_id,
        request.new_name,
    )


@router.delete(
    "/{analysis_run_id}",
    response_model=DeleteAnalysisRunResponse,
    summary="Delete a saved analysis run",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def remove_analysis_run(analysis_run_id: int) -> dict:
    return analysis_run_service.delete_saved_analysis_run(analysis_run_id)
