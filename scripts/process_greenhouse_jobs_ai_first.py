"""Process a small Greenhouse job sample using AI-first skill extraction.

Input:
    data/raw/greenhouse_jobs.csv

Output:
    data/processed/greenhouse_ai_processed_jobs_sample.csv

Extraction behavior:
    Gemini primary -> deterministic emergency fallback
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
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "greenhouse_ai_processed_jobs_sample.csv"

REQUIRED_COLUMNS = [
    "job_id",
    "title",
    "company",
    "location",
    "description",
    "experience_level",
]

def select_sample_jobs(
    jobs_df: pd.DataFrame,
    sample_size: int,
    title_query: str | None = None,
    start_row: int = 0,
) -> pd.DataFrame:
    """Select a small sample of jobs for AI-first extraction experiments."""
    selected_df = jobs_df.copy()

    if title_query:
        selected_df = selected_df[
            selected_df["title"].str.contains(title_query, case=False, na=False)
        ]

    if start_row > 0:
        selected_df = selected_df.iloc[start_row:]

    return selected_df.head(sample_size).copy()

def main(
    sample_size: int = 5,
    delay_seconds: int = 10,
    title_query: str | None = None,
    start_row: int = 0,
    output_path: Path = OUTPUT_PATH,
) -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run scripts/fetch_greenhouse_jobs.py first."
        )

    raw_jobs_df = pd.read_csv(INPUT_PATH)

    missing_columns = set(REQUIRED_COLUMNS) - set(raw_jobs_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    sample_df = select_sample_jobs(
        jobs_df=raw_jobs_df,
        sample_size=sample_size,
        title_query=title_query,
        start_row=start_row,
    )

    if sample_df.empty:
        raise ValueError("No jobs matched the requested sample filters.")

    processed_rows: list[dict[str, object]] = []

    for index, row in sample_df.iterrows():
        title = str(row["title"])
        description = str(row["description"])

        print(f"Processing row {index}: {title}")

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

        if extraction_result.error:
            print(f"  Provider: {extraction_result.provider}")
            print(f"  Error: {extraction_result.error}")
        else:
            print(f"  Provider: {extraction_result.provider}")

        print(f"  Skills: {extraction_result.skills}")

        processed_row = row.to_dict()
        processed_row["clean_title"] = normalize_text(title)
        processed_row["clean_description"] = normalize_text(description)
        processed_row["extracted_skills"] = extraction_result.skills
        processed_row["skills_text"] = ", ".join(extraction_result.skills)
        processed_row["role_category"] = categorize_role(title, description)
        processed_row["skill_extraction_provider"] = extraction_result.provider
        processed_row["skill_extraction_error"] = extraction_result.error
        processed_row["skill_extraction_model"] = getattr(
            extraction_result,
            "model",
            "",
        )
        processed_row["skill_extraction_prompt_version"] = getattr(
            extraction_result,
            "prompt_version",
            "",
        )

        processed_rows.append(processed_row)

        time.sleep(delay_seconds)

    output_df = pd.DataFrame(processed_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)

    print(f"\nSaved AI-first processed sample to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process a small Greenhouse sample using AI-first skill extraction."
    )
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--delay-seconds", type=int, default=10)
    parser.add_argument("--title-query", type=str, default=None)
    parser.add_argument("--start-row", type=int, default=0)
    parser.add_argument(
        "--output-path",
        type=Path,
        default=OUTPUT_PATH,
        help="Where to save the AI-first processed sample CSV.",
    )

    args = parser.parse_args()

    main(
        sample_size=args.sample_size,
        delay_seconds=args.delay_seconds,
        title_query=args.title_query,
        start_row=args.start_row,
        output_path=args.output_path,
    )
