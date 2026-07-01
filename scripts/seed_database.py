# scripts/seed_database.py

from pathlib import Path

import pandas as pd

from src.database.repository import seed_processed_jobs_from_dataframe


ALEMBIC_INI_PATH = Path("alembic.ini")
PROCESSED_JOBS_PATH = Path("data/processed/processed_jobs.csv")


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


def main() -> None:
    if not PROCESSED_JOBS_PATH.exists():
        raise FileNotFoundError(
            "data/processed/processed_jobs.csv does not exist. "
            "Run your processing pipeline first."
        )

    run_database_migrations()

    df = pd.read_csv(PROCESSED_JOBS_PATH)

    inserted_count = seed_processed_jobs_from_dataframe(
        df=df,
        dataset_name="sample_jobs",
        source_type="sample_csv",
        replace_existing=True,
    )

    print(f"Seeded {inserted_count} processed jobs into PostgreSQL.")


if __name__ == "__main__":
    main()
