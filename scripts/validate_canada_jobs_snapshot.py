"""Validate a refreshed Canada jobs snapshot before it replaces the baseline."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from math import ceil
from pathlib import Path
import sys

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.canada_jobs import TARGET_ROLE_CATEGORIES


DEFAULT_CANDIDATE_PATH = (
    ROOT_DIR / "data" / "processed" / "canada_jobs_snapshot.csv"
)
REQUIRED_COLUMNS = {
    "job_id",
    "title",
    "company",
    "location",
    "description",
    "source",
    "source_url",
    "fetched_at",
    "role_category",
    "skills_text",
    "skill_extraction_provider",
}
MINIMUM_JOBS = 40
MINIMUM_BASELINE_RATIO = 0.65
MINIMUM_COMPANIES = 12
MINIMUM_LOCATIONS = 8
MINIMUM_SOURCES = 2
MINIMUM_GROQ_COVERAGE = 0.95
MAXIMUM_SNAPSHOT_AGE = timedelta(days=3)


def snapshot_metrics(snapshot_df: pd.DataFrame) -> dict[str, object]:
    """Calculate stable metrics used by validation and PR summaries."""
    provider_values = snapshot_df["skill_extraction_provider"].fillna("")
    groq_coverage = (
        provider_values.str.strip().str.lower().eq("groq").mean()
        if not snapshot_df.empty
        else 0.0
    )
    fetched_at = pd.to_datetime(
        snapshot_df["fetched_at"],
        errors="coerce",
        utc=True,
    )

    return {
        "job_count": len(snapshot_df),
        "company_count": snapshot_df["company"].nunique(),
        "location_count": snapshot_df["location"].nunique(),
        "source_count": snapshot_df["source"].nunique(),
        "role_categories": sorted(
            snapshot_df["role_category"].dropna().unique().tolist()
        ),
        "groq_coverage": float(groq_coverage),
        "oldest_fetched_at": fetched_at.min(),
        "latest_fetched_at": fetched_at.max(),
    }


def validate_snapshot(
    candidate_df: pd.DataFrame,
    *,
    baseline_df: pd.DataFrame | None = None,
    now: datetime | None = None,
) -> tuple[list[str], dict[str, object]]:
    """Return validation errors and candidate metrics."""
    errors: list[str] = []
    missing_columns = sorted(REQUIRED_COLUMNS - set(candidate_df.columns))

    if missing_columns:
        return (
            [f"Missing required columns: {', '.join(missing_columns)}"],
            {},
        )

    metrics = snapshot_metrics(candidate_df)
    job_count = int(metrics["job_count"])

    if job_count < MINIMUM_JOBS:
        errors.append(
            f"Job count {job_count} is below the minimum of {MINIMUM_JOBS}."
        )

    if baseline_df is not None and not baseline_df.empty:
        minimum_from_baseline = ceil(
            len(baseline_df) * MINIMUM_BASELINE_RATIO
        )
        if job_count < minimum_from_baseline:
            errors.append(
                f"Job count {job_count} is below 65% of the "
                f"{len(baseline_df)}-job baseline."
            )

    if int(metrics["company_count"]) < MINIMUM_COMPANIES:
        errors.append(
            f"Company count {metrics['company_count']} is below "
            f"the minimum of {MINIMUM_COMPANIES}."
        )

    if int(metrics["location_count"]) < MINIMUM_LOCATIONS:
        errors.append(
            f"Location count {metrics['location_count']} is below "
            f"the minimum of {MINIMUM_LOCATIONS}."
        )

    if int(metrics["source_count"]) < MINIMUM_SOURCES:
        errors.append(
            f"Source count {metrics['source_count']} is below "
            f"the minimum of {MINIMUM_SOURCES}."
        )

    missing_roles = sorted(
        TARGET_ROLE_CATEGORIES - set(metrics["role_categories"])
    )
    if missing_roles:
        errors.append(
            f"Missing target role categories: {', '.join(missing_roles)}."
        )

    if float(metrics["groq_coverage"]) < MINIMUM_GROQ_COVERAGE:
        errors.append(
            f"Groq coverage {metrics['groq_coverage']:.1%} is below "
            f"the minimum of {MINIMUM_GROQ_COVERAGE:.0%}."
        )

    job_ids = candidate_df["job_id"].fillna("").astype(str).str.strip()
    if job_ids.eq("").any() or not job_ids.is_unique:
        errors.append("Job IDs must be present and unique.")

    source_urls = (
        candidate_df["source_url"].fillna("").astype(str).str.strip()
    )
    if (
        source_urls.eq("").any()
        or not source_urls.is_unique
        or not source_urls.str.startswith("http").all()
    ):
        errors.append("Source URLs must be present, unique, and start with http.")

    if (
        candidate_df["skills_text"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .any()
    ):
        errors.append("Every posting must include extracted skills.")

    oldest_fetched_at = metrics["oldest_fetched_at"]
    current_time = now or datetime.now(UTC)
    if pd.isna(oldest_fetched_at):
        errors.append("Snapshot does not contain a valid fetched_at timestamp.")
    elif oldest_fetched_at.to_pydatetime() < (
        current_time - MAXIMUM_SNAPSHOT_AGE
    ):
        errors.append(
            "One or more snapshot fetch timestamps are more than three days old."
        )

    return errors, metrics


def build_markdown_summary(
    metrics: dict[str, object],
    *,
    baseline_count: int | None = None,
) -> str:
    """Build a compact Markdown quality summary for an automated PR."""
    role_categories = ", ".join(metrics["role_categories"])
    baseline_text = (
        f" (previously {baseline_count})"
        if baseline_count is not None
        else ""
    )

    return "\n".join(
        [
            "## Snapshot Quality",
            "",
            f"- Jobs: **{metrics['job_count']}**{baseline_text}",
            f"- Companies: **{metrics['company_count']}**",
            f"- Locations: **{metrics['location_count']}**",
            f"- Source platforms: **{metrics['source_count']}**",
            f"- Groq extraction coverage: **{metrics['groq_coverage']:.1%}**",
            f"- Role categories: {role_categories}",
            "",
        ]
    )


def main(
    *,
    candidate_path: Path,
    baseline_path: Path | None = None,
    summary_path: Path | None = None,
) -> None:
    candidate_df = pd.read_csv(candidate_path)
    baseline_df = (
        pd.read_csv(baseline_path)
        if baseline_path is not None and baseline_path.exists()
        else None
    )
    errors, metrics = validate_snapshot(
        candidate_df,
        baseline_df=baseline_df,
    )

    if errors:
        formatted_errors = "\n".join(f"- {error}" for error in errors)
        raise ValueError(
            f"Canada snapshot validation failed:\n{formatted_errors}"
        )

    summary = build_markdown_summary(
        metrics,
        baseline_count=len(baseline_df) if baseline_df is not None else None,
    )
    print(summary)

    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(summary, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate a candidate Canada jobs snapshot."
    )
    parser.add_argument(
        "--candidate-path",
        type=Path,
        default=DEFAULT_CANDIDATE_PATH,
    )
    parser.add_argument("--baseline-path", type=Path)
    parser.add_argument("--summary-path", type=Path)
    arguments = parser.parse_args()

    main(
        candidate_path=arguments.candidate_path,
        baseline_path=arguments.baseline_path,
        summary_path=arguments.summary_path,
    )
