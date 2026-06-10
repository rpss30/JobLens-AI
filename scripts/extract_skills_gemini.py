"""Run Gemini skill extraction on a small sample of processed Adzuna jobs.

This is an experiment script only. It does not modify the production processor.
Output:
    data/processed/gemini_skill_extraction_comparison.csv
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.skill_extraction.gemini_extractor import extract_skills_with_gemini


INPUT_PATH = ROOT_DIR / "data" / "processed" / "adzuna_processed_jobs.csv"
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "gemini_skill_extraction_comparison.csv"


def parse_existing_skills(value: object) -> list[str]:
    """Parse existing deterministic extracted_skills from CSV."""
    if isinstance(value, list):
        return value

    if pd.isna(value):
        return []

    if not isinstance(value, str):
        return []

    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []

    if not isinstance(parsed, list):
        return []

    return [skill for skill in parsed if isinstance(skill, str)]


def main(sample_size: int = 5) -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_PATH}. Run the Adzuna processing flow first."
        )

    jobs_df = pd.read_csv(INPUT_PATH)

    required_columns = {"title", "description", "extracted_skills"}
    missing_columns = required_columns - set(jobs_df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    sample_df = jobs_df.head(sample_size).copy()

    comparison_rows: list[dict[str, object]] = []

    for index, row in sample_df.iterrows():
        title = str(row["title"])
        description = str(row["description"])

        print(f"Extracting skills for row {index}: {title}")

        try:
            gemini_result = extract_skills_with_gemini(
                title=title,
                description=description,
                max_skills=20,
            )
            gemini_skills = gemini_result.skills
            error = ""
        except Exception as exc:
            gemini_skills = []
            error = f"{type(exc).__name__}: {exc}"

        existing_skills = parse_existing_skills(row["extracted_skills"])

        comparison_rows.append(
            {
                "title": title,
                "company": row.get("company", ""),
                "location": row.get("location", ""),
                "deterministic_skills": existing_skills,
                "gemini_skills": gemini_skills,
                "gemini_only_skills": sorted(set(gemini_skills) - set(existing_skills)),
                "deterministic_only_skills": sorted(
                    set(existing_skills) - set(gemini_skills)
                ),
                "error": error,
            }
        )

    output_df = pd.DataFrame(comparison_rows)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved comparison to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()