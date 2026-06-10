"""Build a small mixed-role Greenhouse demo dataset using AI-first extraction.

Input:
    data/raw/greenhouse_jobs.csv

Output:
    data/processed/greenhouse_ai_demo_jobs.csv

Extraction behavior:
    Groq primary -> Gemini fallback -> deterministic emergency fallback

This script is intended to create a small local demo dataset for the dashboard,
not to batch-process thousands of jobs.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.processing.job_processor import categorize_role, normalize_text
from src.skill_extraction.extraction_service import extract_skills_ai_first


INPUT_PATH = ROOT_DIR / "data" / "raw" / "greenhouse_jobs.csv"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "greenhouse_ai_demo_jobs.csv"

DEFAULT_TITLE_QUERIES = [
    "AI Engineer",
    "Backend Software Engineer",
    "Data Scientist",
    "Data Engineer",
    "Platform Engineer",
    "Analytics Engineer",
]

REQUIRED_COLUMNS = [
    "job_id",
    "title",
    "company",
    "location",
    "description",
    "experience_level",
]


def select_jobs_for_queries(
    jobs_df: pd.DataFrame,
    title_queries: list[str],
    jobs_per_query: int,
) -> pd.DataFrame:
    """Select a small deduplicated set of jobs across title queries."""
    selected_frames: list[pd.DataFrame] = []

    for title_query in title_queries:
        query_matches = jobs_df[
            jobs_df["title"].str.contains(title_query, case=False, na=False)
        ].head(jobs_per_query)

        selected_frames.append(query_matches)

    if not selected_frames:
        return pd.DataFrame(columns=jobs_df.columns)

    selected_df = pd.concat(selected_frames, ignore_index=True)

    if "job_id" in selected_df.columns:
        selected_df = selected_df.drop_duplicates(subset=["job_id"])
    else:
        selected_df = selected_df.drop_duplicates()

    return selected_df.reset_index(drop=True)


def process_jobs_with_ai(
    jobs_df: pd.DataFrame,
    delay_seconds: int,
) -> pd.DataFrame:
    """Process selected jobs using AI-first skill extraction."""
    processed_rows: list[dict[str, object]] = []

    for index, row in jobs_df.iterrows():
        title = str(row["title"])
        description = str(row["description"])

        print(f"Processing selected row {index}: {title}")

        extraction_result = extract_skills_ai_first(
            title=title,
            description=description,
            use_groq_primary=True,
            use_gemini_fallback=True,
            use_deterministic_fallback=True,
            max_groq_attempts=1,
            max_gemini_attempts=1,
            retry_delay_seconds=5,
        )

        print(f"  Provider: {extraction_result.provider}")
        print(f"  Skills: {extraction_result.skills}")

        if extraction_result.error:
            print(f"  Error: {extraction_result.error}")

        processed_row = row.to_dict()
        processed_row["clean_title"] = normalize_text(title)
        processed_row["clean_description"] = normalize_text(description)
        processed_row["extracted_skills"] = extraction_result.skills
        processed_row["skills_text"] = ", ".join(extraction_result.skills)
        processed_row["role_category"] = categorize_role(title, description)
        processed_row["skill_extraction_provider"] = extraction_result.provider
        processed_row["skill_extraction_error"] = extraction_result.error

        processed_rows.append(processed_row)

        time.sleep(delay_seconds)

    return pd.DataFrame(processed_rows)


def main(
    jobs_per_query: int = 2,
    delay_seconds: int = 3,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    title_queries: list[str] | None = None,
) -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run scripts/fetch_greenhouse_jobs.py first."
        )

    raw_jobs_df = pd.read_csv(INPUT_PATH)

    missing_columns = set(REQUIRED_COLUMNS) - set(raw_jobs_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    selected_queries = title_queries or DEFAULT_TITLE_QUERIES

    selected_jobs_df = select_jobs_for_queries(
        jobs_df=raw_jobs_df,
        title_queries=selected_queries,
        jobs_per_query=jobs_per_query,
    )

    if selected_jobs_df.empty:
        raise ValueError("No Greenhouse jobs matched the requested title queries.")

    print(f"Selected {len(selected_jobs_df)} jobs for AI-first demo processing.")

    processed_df = process_jobs_with_ai(
        jobs_df=selected_jobs_df,
        delay_seconds=delay_seconds,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed_df.to_csv(output_path, index=False)

    print(f"\nSaved mixed AI demo dataset to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a small mixed-role Greenhouse AI demo dataset."
    )
    parser.add_argument("--jobs-per-query", type=int, default=2)
    parser.add_argument("--delay-seconds", type=int, default=3)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--title-query",
        action="append",
        dest="title_queries",
        help=(
            "Title query to include. Can be passed multiple times. "
            "Defaults to a mixed AI/data/backend/cloud/analytics set."
        ),
    )

    args = parser.parse_args()

    main(
        jobs_per_query=args.jobs_per_query,
        delay_seconds=args.delay_seconds,
        output_path=args.output_path,
        title_queries=args.title_queries,
    )