"""Fetch real job postings from public Lever job boards.

Output:
    data/raw/lever_jobs.csv

This script uses public Lever postings endpoints and normalizes results into
the JobLens raw job schema.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.lever_client import fetch_lever_postings, normalize_lever_posting


OUTPUT_PATH = ROOT_DIR / "data" / "raw" / "lever_jobs.csv"

COMPANY_SLUGS = [
    "figma",
    "scaleai",
    "benchling",
    "verkada",
    "anduril",
    "samsara",
    "ramp",
    "databricks",
    "doordash",
    "reddit",
]

TARGET_KEYWORDS = [
    "machine learning",
    "ml engineer",
    "ai engineer",
    "data scientist",
    "data science",
    "data engineer",
    "analytics",
    "backend",
    "software engineer",
    "cloud",
    "platform engineer",
    "devops",
    "infrastructure",
]


def is_target_job(job: dict[str, object]) -> bool:
    """Return True if a normalized job looks relevant to JobLens target roles."""
    searchable_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    return any(keyword in searchable_text for keyword in TARGET_KEYWORDS)


def main() -> None:
    normalized_jobs: list[dict[str, object]] = []

    for company_slug in COMPANY_SLUGS:
        print(f"Fetching Lever postings for: {company_slug}")

        try:
            postings = fetch_lever_postings(company_slug)
        except requests.RequestException as exc:
            print(f"  Skipped {company_slug}: request failed: {exc}")
            continue
        except ValueError as exc:
            print(f"  Skipped {company_slug}: invalid response: {exc}")
            continue

        for posting in postings:
            normalized = normalize_lever_posting(posting, company_slug=company_slug)

            normalized["is_target_job"] = is_target_job(normalized)
            normalized_jobs.append(normalized)

        target_count = sum(bool(job.get("is_target_job")) for job in normalized_jobs)
        print(f"  Jobs so far: {len(normalized_jobs)} total, {target_count} target-role matches")

    output_columns = [
        "job_id",
        "title",
        "company",
        "location",
        "description",
        "experience_level",
        "source",
        "source_url",
        "fetched_at",
        "is_target_job",
    ]

    output_df = pd.DataFrame(normalized_jobs, columns=output_columns)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved {len(output_df)} Lever jobs to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()