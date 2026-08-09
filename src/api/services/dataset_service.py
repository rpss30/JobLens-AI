from typing import Literal

from src.api.errors import ApiError
from src.api.services.listing import filter_items, paginate_items, sort_items
from src.database import repository as database_repository


DatasetSortBy = Literal["created_at", "name", "source_type"]


def list_dataset_summaries(
    *,
    source_type: str | None = None,
    sort_by: DatasetSortBy = "created_at",
    sort_order: str = "desc",
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so datasets cannot be listed.",
        )

    datasets = database_repository.list_datasets()
    datasets = filter_items(datasets, {"source_type": source_type})
    datasets = sort_items(datasets, sort_by=sort_by, sort_order=sort_order)
    return paginate_items(datasets, limit=limit, offset=offset)


def delete_user_dataset(dataset_name: str) -> dict[str, bool | str]:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so datasets cannot be deleted.",
        )

    try:
        deleted = database_repository.delete_dataset(dataset_name)
    except ValueError as error:
        raise ApiError(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise ApiError(
            status_code=500,
            detail=f"Could not delete dataset '{dataset_name}'.",
        ) from error

    if not deleted:
        raise ApiError(
            status_code=404,
            detail=f"Dataset '{dataset_name}' was not found.",
        )

    return {
        "dataset_name": dataset_name,
        "deleted": True,
    }


def rename_user_dataset(
    dataset_name: str,
    new_name: str,
) -> dict[str, bool | str]:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so datasets cannot be renamed.",
        )

    try:
        renamed = database_repository.rename_dataset(dataset_name, new_name)
    except ValueError as error:
        raise ApiError(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise ApiError(
            status_code=500,
            detail=f"Could not rename dataset '{dataset_name}'.",
        ) from error

    if not renamed:
        raise ApiError(
            status_code=404,
            detail=f"Dataset '{dataset_name}' was not found.",
        )

    return {
        "old_name": dataset_name,
        "new_name": database_repository.build_custom_dataset_name(new_name),
        "renamed": True,
    }
