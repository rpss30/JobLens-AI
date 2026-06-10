"""Fetch real job postings from public Greenhouse job boards.

Output:
    data/raw/greenhouse_jobs.csv

This script uses public Greenhouse job board endpoints and normalizes results
into the JobLens raw job schema.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.greenhouse_client import (
    fetch_greenhouse_jobs,
    normalize_greenhouse_job,
)


OUTPUT_PATH = ROOT_DIR / "data" / "raw" / "greenhouse_jobs.csv"

COMPANY_SLUGS = [
    "airbnb",
    "stripe",
    "datadog",
    "mongodb",
    "cloudflare",
    "anthropic",
    "faire",
    "wealthsimple",
    "neo4j",
    "okta",
]

TARGET_KEYWORDS = [
    "machine learning",
    "ml engineer",
    "ai engineer",
    "artificial intelligence",
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
    "aws",
    "python",
    "sql",
]


OUTPUT_COLUMNS = [
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


def is_target_job(job: dict[str, object]) -> bool:
    """Return True if a normalized job looks relevant to JobLens target roles."""
    searchable_text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    return any(keyword in searchable_text for keyword in TARGET_KEYWORDS)


def main() -> None:
    normalized_jobs: list[dict[str, object]] = []

    for company_slug in COMPANY_SLUGS:
        print(f"Fetching Greenhouse jobs for: {company_slug}")

        try:
            jobs = fetch_greenhouse_jobs(company_slug)
        except requests.RequestException as exc:
            print(f"  Skipped {company_slug}: request failed: {exc}")
            continue
        except ValueError as exc:
            print(f"  Skipped {company_slug}: invalid response: {exc}")
            continue

        for job in jobs:
            normalized = normalize_greenhouse_job(job, company_slug=company_slug)
            normalized["is_target_job"] = is_target_job(normalized)
            normalized_jobs.append(normalized)

        target_count = sum(bool(job.get("is_target_job")) for job in normalized_jobs)
        print(f"  Jobs so far: {len(normalized_jobs)} total, {target_count} target-role matches")

    output_df = pd.DataFrame(normalized_jobs, columns=OUTPUT_COLUMNS)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved {len(output_df)} Greenhouse jobs to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()