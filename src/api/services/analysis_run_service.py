from typing import Literal

from src.api.errors import ApiError
from src.api.services.listing import filter_items, paginate_items, sort_items
from src.database import repository as database_repository


AnalysisRunSortBy = Literal[
    "created_at",
    "name",
    "dataset_name",
    "weighted_match_score",
    "jobs_analyzed",
]


def list_saved_analysis_runs(
    *,
    dataset_name: str | None = None,
    sort_by: AnalysisRunSortBy = "created_at",
    sort_order: str = "desc",
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so analysis runs cannot be listed.",
        )

    analysis_runs = database_repository.list_analysis_runs()
    analysis_runs = filter_items(analysis_runs, {"dataset_name": dataset_name})
    analysis_runs = sort_items(
        analysis_runs,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return paginate_items(analysis_runs, limit=limit, offset=offset)


def get_saved_analysis_run(analysis_run_id: int) -> dict:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so analysis runs cannot be loaded.",
        )

    analysis_run = database_repository.load_analysis_run(analysis_run_id)

    if analysis_run is None:
        raise ApiError(
            status_code=404,
            detail=f"Analysis run {analysis_run_id} was not found.",
        )

    return analysis_run
