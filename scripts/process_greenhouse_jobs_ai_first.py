"""Process a small Greenhouse job sample using AI-first skill extraction.

Input:
    data/raw/greenhouse_jobs.csv

Output:
    data/processed/greenhouse_ai_processed_jobs_sample.csv

Extraction behavior:
    Gemini primary -> deterministic emergency fallback
"""

from __future__ import annotations

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


def main(sample_size: int = 5, delay_seconds: int = 10) -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run scripts/fetch_greenhouse_jobs.py first."
        )

    raw_jobs_df = pd.read_csv(INPUT_PATH)

    missing_columns = set(REQUIRED_COLUMNS) - set(raw_jobs_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    sample_df = raw_jobs_df.head(sample_size).copy()

    processed_rows: list[dict[str, object]] = []

    for index, row in sample_df.iterrows():
        title = str(row["title"])
        description = str(row["description"])

        print(f"Processing row {index}: {title}")

        extraction_result = extract_skills_ai_first(
            title=title,
            description=description,
            use_deterministic_fallback=True,
            max_gemini_attempts=2,
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

        processed_rows.append(processed_row)

        time.sleep(delay_seconds)

    output_df = pd.DataFrame(processed_rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved AI-first processed sample to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()