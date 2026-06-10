"""Run Gemini skill extraction on a small sample of Greenhouse jobs.

Input:
    data/raw/greenhouse_jobs.csv

Output:
    data/processed/greenhouse_gemini_skill_extraction_comparison.csv

This is an experiment script only. It does not modify the production processor.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.skill_extraction.gemini_extractor import extract_skills_with_gemini


INPUT_PATH = ROOT_DIR / "data" / "raw" / "greenhouse_jobs.csv"
OUTPUT_PATH = (
    ROOT_DIR / "data" / "processed" / "greenhouse_gemini_skill_extraction_comparison.csv"
)


def main(sample_size: int = 5, delay_seconds: int = 15) -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run scripts/fetch_greenhouse_jobs.py first."
        )

    jobs_df = pd.read_csv(INPUT_PATH)

    required_columns = {"title", "company", "location", "description", "is_target_job"}
    missing_columns = required_columns - set(jobs_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    target_jobs_df = jobs_df[jobs_df["is_target_job"] == True].copy()  # noqa: E712
    sample_df = target_jobs_df.head(sample_size).copy()

    comparison_rows: list[dict[str, object]] = []

    for index, row in sample_df.iterrows():
        title = str(row["title"])
        description = str(row["description"])

        print(f"Extracting skills for row {index}: {title}")

        try:
            gemini_result = extract_skills_with_gemini(
                title=title,
                description=description,
                max_skills=25,
            )
            gemini_skills = gemini_result.skills
            raw_response = gemini_result.raw_response
            error = ""
        except Exception as exc:
            gemini_skills = []
            raw_response = ""
            error = f"{type(exc).__name__}: {exc}"
            
        if error:
            print(f"  Error: {error}")
        else:
            print(f"  Skills: {gemini_skills}")

        time.sleep(delay_seconds)

        comparison_rows.append(
            {
                "title": title,
                "company": row.get("company", ""),
                "location": row.get("location", ""),
                "description_length": len(description),
                "gemini_skills": gemini_skills,
                "raw_response": raw_response,
                "error": error,
            }
        )

    output_df = pd.DataFrame(comparison_rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved comparison to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()