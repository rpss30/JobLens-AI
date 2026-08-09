import logging
import tempfile
from pathlib import Path
from typing import Literal

import pandas as pd

from src.api.errors import ApiError
from src.api.services.listing import filter_items, paginate_items, sort_items
from src.dashboard.services import (
    ALLOWED_UPLOAD_EXTENSIONS,
    MAX_UPLOADED_CSV_BYTES,
    read_uploaded_jobs_csv,
    validate_uploaded_jobs_csv,
)
from src.database import repository as database_repository
from src.processing.job_processor import process_jobs


logger = logging.getLogger("joblens.api")


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


def create_uploaded_dataset(
    *,
    filename: str,
    content: bytes,
    dataset_name: str,
) -> dict[str, str | int]:
    """Validate, process, and persist an uploaded jobs CSV as a new dataset."""
    if not database_repository.check_database_connection():
        raise ApiError(
            status_code=503,
            detail="PostgreSQL is unavailable, so datasets cannot be uploaded.",
        )

    if not dataset_name.strip():
        raise ApiError(status_code=400, detail="Provide a dataset name.")

    # The temp file always ends in .csv, so the original name carries the check.
    uploaded_suffix = Path(filename).suffix.lower()

    if uploaded_suffix and uploaded_suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ApiError(
            status_code=400,
            detail="Uploaded file must be a CSV file.",
        )

    if not content:
        raise ApiError(
            status_code=400,
            detail="Uploaded CSV is empty. Please upload a valid jobs CSV.",
        )

    if len(content) > MAX_UPLOADED_CSV_BYTES:
        max_size_mb = MAX_UPLOADED_CSV_BYTES / (1024 * 1024)
        raise ApiError(
            status_code=400,
            detail=f"Uploaded CSV must be {max_size_mb:.0f} MB or smaller.",
        )

    # Reuse the dashboard's upload rules so both surfaces accept the same files.
    with tempfile.TemporaryDirectory(prefix="joblens_api_upload_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        raw_path = temp_dir_path / "uploaded_jobs.csv"
        processed_path = temp_dir_path / "uploaded_processed_jobs.csv"

        raw_path.write_bytes(content)

        try:
            uploaded_jobs_df = read_uploaded_jobs_csv(raw_path)
        except ValueError as error:
            raise ApiError(status_code=400, detail=str(error)) from error
        except pd.errors.EmptyDataError as error:
            raise ApiError(
                status_code=400,
                detail="Uploaded CSV is empty. Please upload a valid jobs CSV.",
            ) from error
        except pd.errors.ParserError as error:
            raise ApiError(
                status_code=400,
                detail=(
                    "Uploaded file could not be parsed as a valid CSV. "
                    "Please check the file formatting."
                ),
            ) from error
        except UnicodeDecodeError as error:
            raise ApiError(
                status_code=400,
                detail=(
                    "Uploaded CSV could not be decoded. "
                    "Please save it as UTF-8 and try again."
                ),
            ) from error

        is_valid_upload, validation_message = validate_uploaded_jobs_csv(
            uploaded_jobs_df
        )

        if not is_valid_upload:
            raise ApiError(status_code=400, detail=validation_message)

        uploaded_jobs_df.to_csv(raw_path, index=False)

        try:
            processed_jobs_df = process_jobs(
                input_path=str(raw_path),
                output_path=str(processed_path),
            )
        except Exception as error:
            logger.exception("Could not process uploaded dataset")
            raise ApiError(
                status_code=400,
                detail="Uploaded CSV could not be processed into job postings.",
            ) from error

    if processed_jobs_df.empty:
        raise ApiError(
            status_code=400,
            detail=(
                "Uploaded CSV was processed, but no usable job postings were found."
            ),
        )

    try:
        saved_dataset_name = database_repository.save_uploaded_dataset_from_dataframe(
            df=processed_jobs_df,
            filename=filename,
            custom_name=dataset_name,
        )
    except ValueError as error:
        raise ApiError(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Could not save uploaded dataset")
        raise ApiError(
            status_code=500,
            detail="Uploaded dataset could not be saved to PostgreSQL.",
        ) from error

    return {
        "dataset_name": saved_dataset_name,
        "job_count": len(processed_jobs_df),
    }


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
