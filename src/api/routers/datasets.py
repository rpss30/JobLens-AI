from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from src.api.query_params import ListQueryParams, pagination_params
from src.api.schemas import (
    DatasetSummary,
    DeleteDatasetResponse,
    ErrorResponse,
    RenameDatasetRequest,
    RenameDatasetResponse,
    UploadDatasetResponse,
)
from src.api.services import dataset_service
from src.api.services.dataset_service import DatasetSortBy


router = APIRouter(
    prefix="/datasets",
    tags=["datasets"],
)


@router.get(
    "",
    response_model=list[DatasetSummary],
    summary="List PostgreSQL datasets",
    responses={503: {"model": ErrorResponse}},
)
def get_datasets(
    query: Annotated[ListQueryParams, Depends(pagination_params)],
    source_type: Annotated[
        str | None,
        Query(
            max_length=50,
            description="Optional exact source type filter.",
        ),
    ] = None,
    sort_by: Annotated[
        DatasetSortBy,
        Query(description="Dataset field to sort by."),
    ] = "created_at",
) -> list[dict]:
    return dataset_service.list_dataset_summaries(
        source_type=source_type,
        sort_by=sort_by,
        sort_order=query.sort_order,
        limit=query.limit,
        offset=query.offset,
    )


@router.post(
    "",
    response_model=UploadDatasetResponse,
    status_code=201,
    summary="Upload a jobs CSV as a new dataset",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def upload_dataset(
    file: Annotated[UploadFile, File(description="Jobs CSV to upload.")],
    dataset_name: Annotated[
        str,
        Form(
            max_length=120,
            description="Name for the saved dataset. Stored as a slug.",
        ),
    ],
) -> dict[str, str | int]:
    return dataset_service.create_uploaded_dataset(
        filename=file.filename or "uploaded_jobs.csv",
        content=await file.read(),
        dataset_name=dataset_name,
    )


@router.delete(
    "/{dataset_name}",
    response_model=DeleteDatasetResponse,
    summary="Delete an uploaded dataset",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def remove_dataset(dataset_name: str) -> dict[str, bool | str]:
    return dataset_service.delete_user_dataset(dataset_name)


@router.patch(
    "/{dataset_name}",
    response_model=RenameDatasetResponse,
    summary="Rename an uploaded dataset",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def update_dataset_name(
    dataset_name: str,
    request: RenameDatasetRequest,
) -> dict[str, bool | str]:
    return dataset_service.rename_user_dataset(dataset_name, request.new_name)
