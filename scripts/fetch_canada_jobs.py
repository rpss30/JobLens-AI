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
from src.ingestion.pipeline_runs import (
    FAILED_STATUS,
    IngestionRunSummary,
    SUCCESS_STATUS,
    SourceFetchResult,
    build_ingestion_run_summary,
    build_markdown_run_summary,
    current_utc_time,
    validate_job_records,
    write_markdown_run_summary,
    write_run_summary,
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


def fetch_all_sources_with_results(
    sources: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[SourceFetchResult]]:
    """Fetch all sources while retaining failures for a run summary."""
    jobs: list[dict[str, object]] = []
    source_results: list[SourceFetchResult] = []

    for source in sources:
        company = source["company"]
        source_type = source["source_type"]
        source_identifier = source["source_identifier"]
        print(f"Fetching {company} ({source_type})...")

        try:
            source_jobs = fetch_source_jobs(source)
        except (requests.RequestException, ValueError) as error:
            error_text = f"{type(error).__name__}: {error}"
            source_results.append(
                SourceFetchResult(
                    company=company,
                    source_type=source_type,
                    source_identifier=source_identifier,
                    status=FAILED_STATUS,
                    error=error_text,
                )
            )
            print(f"  Skipped: {error}")
            continue

        jobs.extend(source_jobs)
        source_results.append(
            SourceFetchResult(
                company=company,
                source_type=source_type,
                source_identifier=source_identifier,
                status=SUCCESS_STATUS,
                job_count=len(source_jobs),
            )
        )
        print(f"  Loaded {len(source_jobs)} active source postings.")

    return jobs, source_results


def fetch_all_sources(
    sources: list[dict[str, str]],
) -> tuple[list[dict[str, object]], list[str]]:
    """Fetch all sources while retaining failures for backwards compatibility."""
    jobs, source_results = fetch_all_sources_with_results(sources)
    errors = [
        f"{result.company}: {result.error}"
        for result in source_results
        if result.error
    ]

    return jobs, errors


def save_run_summary_to_database(
    summary: IngestionRunSummary,
    *,
    dataset_name: str | None,
) -> None:
    from src.database.repository import save_ingestion_run_summary

    save_ingestion_run_summary(
        summary,
        dataset_name=dataset_name,
        dataset_source_type="canada_snapshot" if dataset_name else None,
    )


def main(
    *,
    source_path: Path = DEFAULT_SOURCE_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    summary_path: Path | None = None,
    summary_markdown_path: Path | None = None,
    save_run_to_db: bool = False,
    dataset_name: str | None = "canada_jobs",
) -> None:
    started_at = current_utc_time()
    sources = load_employer_sources(source_path)
    fetched_jobs, source_results = fetch_all_sources_with_results(sources)
    canada_jobs = prepare_canada_jobs(fetched_jobs)
    validation_errors = validate_job_records(canada_jobs)
    summary = build_ingestion_run_summary(
        source_type="canada_jobs_fetch",
        started_at=started_at,
        completed_at=current_utc_time(),
        source_results=source_results,
        raw_job_count=len(fetched_jobs),
        processed_job_count=len(canada_jobs),
        validation_errors=validation_errors,
        metadata={
            "source_path": str(source_path),
            "output_path": str(output_path),
        },
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(canada_jobs).to_csv(output_path, index=False)

    if summary_path is not None:
        write_run_summary(summary, summary_path)

    if summary_markdown_path is not None:
        write_markdown_run_summary(summary, summary_markdown_path)

    if save_run_to_db:
        save_run_summary_to_database(summary, dataset_name=dataset_name)

    print(f"\nFetched {len(fetched_jobs)} total source postings.")
    print(f"Saved {len(canada_jobs)} Canadian technical postings to {output_path}.")
    print()
    print(build_markdown_run_summary(summary))

    if summary.error_log:
        print(f"{len(summary.error_log)} ingestion issues:")
        for error in summary.error_log:
            print(f"  - {error}")

    if validation_errors:
        formatted_errors = "\n".join(f"- {error}" for error in validation_errors)
        raise ValueError(f"Canada jobs fetch validation failed:\n{formatted_errors}")


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
    parser.add_argument("--summary-path", type=Path)
    parser.add_argument("--summary-markdown-path", type=Path)
    parser.add_argument("--save-run-to-db", action="store_true")
    parser.add_argument("--dataset-name", default="canada_jobs")
    arguments = parser.parse_args()

    main(
        source_path=arguments.source_path,
        output_path=arguments.output_path,
        summary_path=arguments.summary_path,
        summary_markdown_path=arguments.summary_markdown_path,
        save_run_to_db=arguments.save_run_to_db,
        dataset_name=arguments.dataset_name,
    )
