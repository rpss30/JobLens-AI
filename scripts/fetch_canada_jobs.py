"""Fetch and normalize current Canadian technical jobs from employer boards."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.ashby_client import (
    fetch_ashby_postings,
    normalize_ashby_posting,
)
from src.ingestion.canada_jobs import prepare_canada_jobs
from src.ingestion.greenhouse_client import (
    fetch_greenhouse_jobs,
    normalize_greenhouse_job,
)
from src.ingestion.lever_client import (
    fetch_lever_postings,
    normalize_lever_posting,
)


DEFAULT_SOURCE_PATH = ROOT_DIR / "data" / "sources" / "canada_employers.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "raw" / "canada_jobs.csv"


def load_employer_sources(path: Path) -> list[dict[str, str]]:
    """Load and validate the employer source registry."""
    sources = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(sources, list):
        raise ValueError("Employer source registry must contain a JSON list.")

    required_fields = {"company", "source_type", "source_identifier"}

    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Every employer source must be a JSON object.")

        missing_fields = required_fields - set(source)
        if missing_fields:
            raise ValueError(
                f"Employer source is missing fields: {sorted(missing_fields)}"
            )

    return sources


def fetch_source_jobs(source: dict[str, str]) -> list[dict[str, object]]:
    """Fetch and normalize postings for one configured employer source."""
    company = source["company"]
    source_type = source["source_type"]
    identifier = source["source_identifier"]

    if source_type == "greenhouse":
        return [
            {
                **normalize_greenhouse_job(
                    posting,
                    company_slug=identifier,
                ),
                "company": company,
            }
            for posting in fetch_greenhouse_jobs(identifier)
        ]

    if source_type == "lever":
        return [
            {
                **normalize_lever_posting(
                    posting,
                    company_slug=identifier,
                ),
                "company": company,
            }
            for posting in fetch_lever_postings(identifier)
        ]

    if source_type == "ashby":
        return [
            normalize_ashby_posting(
                posting,
                company_name=company,
                job_board_name=identifier,
            )
            for posting in fetch_ashby_postings(identifier)
        ]

    raise ValueError(f"Unsupported source type: {source_type}")


def fetch_all_sources(
    sources: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[str]]:
    """Fetch all sources while retaining failures for a run summary."""
    jobs: list[dict[str, object]] = []
    errors: list[str] = []

    for source in sources:
        company = source["company"]
        source_type = source["source_type"]
        print(f"Fetching {company} ({source_type})...")

        try:
            source_jobs = fetch_source_jobs(source)
        except (requests.RequestException, ValueError) as error:
            errors.append(f"{company}: {type(error).__name__}: {error}")
            print(f"  Skipped: {error}")
            continue

        jobs.extend(source_jobs)
        print(f"  Loaded {len(source_jobs)} active source postings.")

    return jobs, errors


def main(
    *,
    source_path: Path = DEFAULT_SOURCE_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> None:
    sources = load_employer_sources(source_path)
    fetched_jobs, errors = fetch_all_sources(sources)
    canada_jobs = prepare_canada_jobs(fetched_jobs)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(canada_jobs).to_csv(output_path, index=False)

    print(f"\nFetched {len(fetched_jobs)} total source postings.")
    print(f"Saved {len(canada_jobs)} Canadian technical postings to {output_path}.")

    if errors:
        print(f"{len(errors)} sources failed:")
        for error in errors:
            print(f"  - {error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch current Canadian technical jobs from employer boards."
    )
    parser.add_argument(
        "--source-path",
        type=Path,
        default=DEFAULT_SOURCE_PATH,
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    arguments = parser.parse_args()

    main(
        source_path=arguments.source_path,
        output_path=arguments.output_path,
    )
