"""Fetch real job postings from Adzuna and save them as a raw JobLens dataset.

This script only creates a raw CSV for now. Processing and PostgreSQL saving
will be added after the basic API fetch works.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.adzuna_client import AdzunaClientError, fetch_adzuna_jobs
from src.ingestion.normalizers import RAW_JOB_COLUMNS, normalize_adzuna_jobs


OUTPUT_PATH = ROOT_DIR / "data" / "raw" / "adzuna_jobs.csv"

SEARCH_QUERIES = [
    "Machine Learning Engineer",
    "Data Scientist",
    "AWS Cloud Engineer",
    "Backend Developer",
    "Data Analyst",
]

LOCATIONS = [
    "Toronto",
    "Vancouver",
    "Montreal",
    "Calgary",
    "Ottawa",
]


def fetch_all_jobs(results_per_search: int = 5) -> pd.DataFrame:
    """Fetch and normalize a small batch of Adzuna jobs."""
    all_normalized_jobs: list[dict[str, str]] = []

    for query in SEARCH_QUERIES:
        for location in LOCATIONS:
            print(f"Fetching: {query} in {location}")

            try:
                raw_jobs = fetch_adzuna_jobs(
                    query=query,
                    location=location,
                    results_per_page=results_per_search,
                )
            except AdzunaClientError as error:
                print(f"Skipped {query} in {location}: {error}")
                continue

            normalized_jobs = normalize_adzuna_jobs(raw_jobs)
            all_normalized_jobs.extend(normalized_jobs)

    jobs_df = pd.DataFrame(all_normalized_jobs, columns=RAW_JOB_COLUMNS)

    if jobs_df.empty:
        return jobs_df

    jobs_df = jobs_df.drop_duplicates(subset=["job_id", "title", "company", "location"])
    return jobs_df


def main() -> None:
    """Run the Adzuna ingestion script."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    jobs_df = fetch_all_jobs(results_per_search=5)

    if jobs_df.empty:
        print("No jobs were fetched. Check your Adzuna credentials or search parameters.")
        return

    jobs_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(jobs_df)} jobs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()