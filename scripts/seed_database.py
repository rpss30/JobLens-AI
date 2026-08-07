import argparse
from pathlib import Path

import pandas as pd

from src.database.repository import seed_processed_jobs_from_dataframe


ALEMBIC_INI_PATH = Path("alembic.ini")
PROCESSED_JOBS_PATH = Path("data/processed/processed_jobs.csv")
DEFAULT_DATASET_NAME = "sample_jobs"
DEFAULT_SOURCE_TYPE = "sample_csv"


def run_database_migrations() -> None:
    if not ALEMBIC_INI_PATH.exists():
        raise FileNotFoundError("alembic.ini does not exist.")

    try:
        from alembic import command
        from alembic.config import Config
    except ImportError as exc:
        raise RuntimeError(
            "Alembic is required to migrate the database. "
            "Run `pip install -r requirements.txt` and try again."
        ) from exc

    command.upgrade(Config(str(ALEMBIC_INI_PATH)), "head")


def seed_processed_jobs(
    *,
    processed_jobs_path: Path = PROCESSED_JOBS_PATH,
    dataset_name: str = DEFAULT_DATASET_NAME,
    source_type: str = DEFAULT_SOURCE_TYPE,
    replace_existing: bool = True,
) -> int:
    if not processed_jobs_path.exists():
        raise FileNotFoundError(
            f"{processed_jobs_path} does not exist. "
            "Run your processing pipeline first."
        )

    run_database_migrations()

    df = pd.read_csv(processed_jobs_path)

    inserted_count = seed_processed_jobs_from_dataframe(
        df=df,
        dataset_name=dataset_name,
        source_type=source_type,
        replace_existing=replace_existing,
    )

    print(
        f"Seeded {inserted_count} processed jobs into PostgreSQL "
        f"dataset '{dataset_name}'."
    )

    return inserted_count


def main(
    *,
    processed_jobs_path: Path = PROCESSED_JOBS_PATH,
    dataset_name: str = DEFAULT_DATASET_NAME,
    source_type: str = DEFAULT_SOURCE_TYPE,
    replace_existing: bool = True,
) -> int:
    return seed_processed_jobs(
        processed_jobs_path=processed_jobs_path,
        dataset_name=dataset_name,
        source_type=source_type,
        replace_existing=replace_existing,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed a processed JobLens dataset into PostgreSQL."
    )
    parser.add_argument(
        "--processed-jobs-path",
        type=Path,
        default=PROCESSED_JOBS_PATH,
    )
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--source-type", default=DEFAULT_SOURCE_TYPE)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to the dataset instead of replacing existing rows.",
    )
    args = parser.parse_args()

    main(
        processed_jobs_path=args.processed_jobs_path,
        dataset_name=args.dataset_name,
        source_type=args.source_type,
        replace_existing=not args.append,
    )
