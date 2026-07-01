from typing import Literal

from fastapi import Query
from pydantic import BaseModel


SortOrder = Literal["asc", "desc"]


class ListQueryParams(BaseModel):
    limit: int
    offset: int
    sort_order: SortOrder


def pagination_params(
    limit: int = Query(
        default=100,
        ge=1,
        le=100,
        description="Maximum number of records to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip before returning results.",
    ),
    sort_order: SortOrder = Query(
        default="desc",
        description="Sort direction.",
    ),
) -> ListQueryParams:
    return ListQueryParams(
        limit=limit,
        offset=offset,
        sort_order=sort_order,
    )
