"""Process raw Greenhouse jobs using the existing deterministic skill extractor.

Input:
    data/raw/greenhouse_jobs.csv

Output:
    data/processed/greenhouse_processed_jobs.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.processing.job_processor import process_jobs


INPUT_PATH = ROOT_DIR / "data" / "raw" / "greenhouse_jobs.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "greenhouse_processed_jobs.csv"
TEMP_INPUT_PATH = ROOT_DIR / "data" / "processed" / "_greenhouse_processing_input.csv"

REQUIRED_COLUMNS = [
    "job_id",
    "title",
    "company",
    "location",
    "description",
    "experience_level",
]


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run scripts/fetch_greenhouse_jobs.py first."
        )

    raw_jobs_df = pd.read_csv(INPUT_PATH)

    missing_columns = set(REQUIRED_COLUMNS) - set(raw_jobs_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    jobs_for_processing_df = raw_jobs_df[REQUIRED_COLUMNS].copy()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    jobs_for_processing_df.to_csv(TEMP_INPUT_PATH, index=False)

    processed_jobs_df = process_jobs(TEMP_INPUT_PATH, OUTPUT_PATH)

    for optional_column in ["source", "source_url", "fetched_at", "is_target_job"]:
        if optional_column in raw_jobs_df.columns:
            processed_jobs_df[optional_column] = raw_jobs_df[optional_column]

    processed_jobs_df.to_csv(OUTPUT_PATH, index=False)
    TEMP_INPUT_PATH.unlink(missing_ok=True)

    print(f"Processed {len(processed_jobs_df)} Greenhouse jobs.")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()