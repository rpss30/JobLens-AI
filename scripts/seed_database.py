# scripts/seed_database.py

from pathlib import Path

import pandas as pd

from src.database.init_db import init_db
from src.database.repository import seed_processed_jobs_from_dataframe


PROCESSED_JOBS_PATH = Path("data/processed/processed_jobs.csv")


def main() -> None:
    if not PROCESSED_JOBS_PATH.exists():
        raise FileNotFoundError(
            "data/processed/processed_jobs.csv does not exist. "
            "Run your processing pipeline first."
        )

    init_db()

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