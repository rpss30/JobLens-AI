"""Keeping and dropping job postings.

Saves are not attached to a person: the product has no user model, and
analysis runs are stored the same way. So a save is a fact about the
installation rather than about a reader, which is the honest shape for it
until there is somewhere for a reader to exist.
"""

from src.api.errors import ApiError
from src.api.schemas import SaveJobRequest
from src.database import repository as database_repository


def list_kept_jobs(dataset_name: str | None = None) -> list[dict]:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so saved jobs cannot be listed.",
        )

    return database_repository.list_saved_jobs(dataset_name=dataset_name)


def keep_job(request: SaveJobRequest) -> dict:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so the job cannot be saved.",
        )

    return database_repository.save_job(
        job_id=request.job_id,
        dataset_name=request.dataset_name,
        title=request.title,
        company=request.company,
        location=request.location,
        source_url=request.source_url,
        date_posted=request.date_posted,
        experience_level=request.experience_level,
    )


def drop_kept_job(*, job_id: str, dataset_name: str) -> dict:
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so the job cannot be unsaved.",
        )

    deleted = database_repository.delete_saved_job(
        job_id=job_id,
        dataset_name=dataset_name,
    )

    if not deleted:
        raise ApiError(status_code=404, detail="That job is not saved.")

    return {"job_id": job_id, "deleted": True}
