"""Build the packaged global early-career jobs dataset."""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.job_page_hydrator import hydrate_job_page
from src.ingestion.pipeline_runs import (
    build_markdown_run_summary,
    build_single_stage_run_summary,
    current_utc_time,
    validate_job_records,
    write_markdown_run_summary,
    write_run_summary,
)
from src.processing.job_processor import categorize_role, extract_skills, normalize_text


DEFAULT_INPUT_PATH = ROOT_DIR / "data" / "raw" / "simplify_new_grad_jobs.csv"
DEFAULT_OUTPUT_PATH = (
    ROOT_DIR / "data" / "processed" / "early_career_global_jobs.csv"
)
SKILL_EXTRACTION_PROVIDER = "deterministic_skill_dictionary"
SKILL_EXTRACTION_MODEL = "deterministic-skill-dictionary"
SKILL_EXTRACTION_PROMPT_VERSION = "deterministic-skill-dictionary-v1"


def metadata_text(value: object, *, default: str = "") -> str:
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    text = str(value).strip()
    return text if text else default


def build_processed_row(
    job: dict[str, object],
    *,
    hydrate_descriptions: bool = True,
    min_hydrated_chars: int = 500,
    timeout_seconds: int = 5,
) -> dict[str, object]:
    """Return a processed early-career job row."""
    title = metadata_text(job.get("title"))
    source_description = metadata_text(job.get("description"))
    source_url = metadata_text(job.get("source_url"))
    hydration_provider = "source_index"
    hydration_status_code: int | str = ""
    hydration_error = ""
    description = source_description

    if hydrate_descriptions:
        hydration_result = hydrate_job_page(
            source_url,
            min_text_chars=min_hydrated_chars,
            timeout_seconds=timeout_seconds,
        )
        hydration_provider = hydration_result.provider
        hydration_status_code = hydration_result.status_code or ""
        hydration_error = hydration_result.error

        if hydration_result.description:
            description = hydration_result.description

    clean_title = normalize_text(title)
    clean_description = normalize_text(description)
    skills = extract_skills(description)

    return {
        **job,
        "description": description,
        "description_formatted": description,
        "clean_title": clean_title,
        "clean_description": clean_description,
        "extracted_skills": skills,
        "skills_text": ", ".join(skills),
        "role_category": categorize_role(title, description),
        "skill_extraction_provider": SKILL_EXTRACTION_PROVIDER,
        "skill_extraction_error": "",
        "skill_extraction_model": SKILL_EXTRACTION_MODEL,
        "skill_extraction_prompt_version": SKILL_EXTRACTION_PROMPT_VERSION,
        "skill_extraction_confidence": 0.5 if skills else 0.0,
        "description_hydration_provider": hydration_provider,
        "description_hydration_status_code": hydration_status_code,
        "description_hydration_error": hydration_error,
    }


def process_early_career_jobs(
    jobs: list[dict[str, object]],
    *,
    hydrate_descriptions: bool = True,
    min_hydrated_chars: int = 500,
    timeout_seconds: int = 5,
    delay_seconds: float = 0.0,
    checkpoint_path: Path | None = None,
) -> list[dict[str, object]]:
    processed_rows: list[dict[str, object]] = []

    for index, job in enumerate(jobs, start=1):
        print(f"[{index}/{len(jobs)}] Processing {job.get('title')}")
        processed_rows.append(
            build_processed_row(
                job,
                hydrate_descriptions=hydrate_descriptions,
                min_hydrated_chars=min_hydrated_chars,
                timeout_seconds=timeout_seconds,
            )
        )

        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(processed_rows).to_csv(checkpoint_path, index=False)

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return processed_rows


def build_snapshot_run_summary(
    *,
    raw_jobs: list[dict[str, object]],
    processed_rows: list[dict[str, object]],
    started_at: datetime,
    output_path: Path,
    validation_errors: list[str],
) -> object:
    hydration_counts = Counter(
        metadata_text(row.get("description_hydration_provider"), default="unknown")
        for row in processed_rows
    )
    skill_covered_count = sum(
        1
        for row in processed_rows
        if metadata_text(row.get("skills_text"))
    )
    skill_coverage = (
        round(skill_covered_count / len(processed_rows), 3)
        if processed_rows
        else 0.0
    )

    return build_single_stage_run_summary(
        source_type="early_career_global_build",
        started_at=started_at,
        completed_at=current_utc_time(),
        raw_job_count=len(raw_jobs),
        processed_job_count=len(processed_rows),
        errors=validation_errors,
        metadata={
            "output_path": str(output_path),
            "hydration_provider_counts": dict(hydration_counts),
            "skill_covered_count": skill_covered_count,
            "skill_coverage": skill_coverage,
        },
    )


def main(
    *,
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    summary_path: Path | None = None,
    summary_markdown_path: Path | None = None,
    hydrate_descriptions: bool = True,
    min_hydrated_chars: int = 500,
    timeout_seconds: int = 5,
    delay_seconds: float = 0.0,
) -> None:
    started_at = current_utc_time()
    raw_jobs_df = pd.read_csv(input_path)
    raw_jobs = raw_jobs_df.to_dict(orient="records")
    processed_rows = process_early_career_jobs(
        raw_jobs,
        hydrate_descriptions=hydrate_descriptions,
        min_hydrated_chars=min_hydrated_chars,
        timeout_seconds=timeout_seconds,
        delay_seconds=delay_seconds,
        checkpoint_path=output_path,
    )
    validation_errors = validate_job_records(processed_rows)
    summary = build_snapshot_run_summary(
        raw_jobs=raw_jobs,
        processed_rows=processed_rows,
        started_at=started_at,
        output_path=output_path,
        validation_errors=validation_errors,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(processed_rows).to_csv(output_path, index=False)

    if summary_path is not None:
        write_run_summary(summary, summary_path)

    if summary_markdown_path is not None:
        write_markdown_run_summary(summary, summary_markdown_path)

    print(f"\nProcessed {len(processed_rows)} early-career postings.")
    print(f"Saved processed dataset to {output_path}.")
    print()
    print(build_markdown_run_summary(summary))

    if validation_errors:
        formatted_errors = "\n".join(f"- {error}" for error in validation_errors)
        raise ValueError(
            f"Early-career snapshot validation failed:\n{formatted_errors}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the packaged global early-career jobs dataset."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=DEFAULT_INPUT_PATH,
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    parser.add_argument("--summary-path", type=Path)
    parser.add_argument("--summary-markdown-path", type=Path)
    parser.add_argument(
        "--skip-hydration",
        action="store_true",
        help="Use Simplify index descriptions without fetching apply pages.",
    )
    parser.add_argument("--min-hydrated-chars", type=int, default=500)
    parser.add_argument("--timeout-seconds", type=int, default=5)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    arguments = parser.parse_args()

    main(
        input_path=arguments.input_path,
        output_path=arguments.output_path,
        summary_path=arguments.summary_path,
        summary_markdown_path=arguments.summary_markdown_path,
        hydrate_descriptions=not arguments.skip_hydration,
        min_hydrated_chars=arguments.min_hydrated_chars,
        timeout_seconds=arguments.timeout_seconds,
        delay_seconds=arguments.delay_seconds,
    )
