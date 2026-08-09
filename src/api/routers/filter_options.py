from typing import Annotated

from fastapi import APIRouter, Query

from src.api.schemas import ErrorResponse, FilterOptionsResponse
from src.api.services import filter_options_service


router = APIRouter(tags=["filter-options"])


@router.get(
    "/filter-options",
    response_model=FilterOptionsResponse,
    summary="List selectable analysis filters for a dataset",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_filter_options(
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
) -> dict:
    return filter_options_service.get_filter_options(dataset_name)
