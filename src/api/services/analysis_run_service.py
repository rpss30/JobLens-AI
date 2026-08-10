from typing import Literal

from src.api.errors import ApiError
from src.api.schemas import CreateAnalysisRunRequest
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


def create_analysis_run(request: CreateAnalysisRunRequest) -> dict:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so analysis runs cannot be saved.",
        )

    analysis_run_name = request.name.strip() or database_repository.build_analysis_run_name(
        best_role=request.best_role,
        dataset_name=request.dataset_name,
    )

    try:
        analysis_run_id = database_repository.save_analysis_run(
            name=analysis_run_name,
            dataset_name=request.dataset_name,
            target_roles=request.target_roles,
            location=request.location,
            experience_level=request.experience_level,
            current_skills=request.current_skills,
            best_role=request.best_role,
            weighted_match_score=request.weighted_match_score,
            top_missing_skill=request.top_missing_skill,
            jobs_analyzed=request.jobs_analyzed,
            recommended_skills=request.recommended_skills,
            role_scores=request.role_scores,
        )
    except Exception as error:
        raise ApiError(
            status_code=500,
            detail="Could not save this analysis run.",
        ) from error

    saved_analysis_run = database_repository.load_analysis_run(analysis_run_id)

    if saved_analysis_run is None:
        raise ApiError(
            status_code=500,
            detail="Analysis run was saved but could not be loaded back.",
        )

    return saved_analysis_run


def rename_saved_analysis_run(analysis_run_id: int, new_name: str) -> dict:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so analysis runs cannot be renamed.",
        )

    try:
        renamed = database_repository.rename_analysis_run(
            analysis_run_id,
            new_name,
        )
    except ValueError as error:
        raise ApiError(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise ApiError(
            status_code=500,
            detail=f"Could not rename analysis run {analysis_run_id}.",
        ) from error

    if not renamed:
        raise ApiError(
            status_code=404,
            detail=f"Analysis run {analysis_run_id} was not found.",
        )

    return {
        "id": analysis_run_id,
        "name": new_name.strip(),
        "renamed": True,
    }


def delete_saved_analysis_run(analysis_run_id: int) -> dict:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so analysis runs cannot be deleted.",
        )

    try:
        deleted = database_repository.delete_analysis_run(analysis_run_id)
    except Exception as error:
        raise ApiError(
            status_code=500,
            detail=f"Could not delete analysis run {analysis_run_id}.",
        ) from error

    if not deleted:
        raise ApiError(
            status_code=404,
            detail=f"Analysis run {analysis_run_id} was not found.",
        )

    return {"id": analysis_run_id, "deleted": True}


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
