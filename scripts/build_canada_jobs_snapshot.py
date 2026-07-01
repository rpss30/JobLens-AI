"""Build a balanced Canada jobs snapshot with Groq-first skill extraction."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import sys
import time
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.canada_jobs import select_balanced_jobs
from src.processing.job_processor import (
    categorize_role,
    extract_skills as extract_skills_deterministic,
    normalize_text,
)
from src.ingestion.pipeline_runs import (
    IngestionRunSummary,
    build_markdown_run_summary,
    build_single_stage_run_summary,
    current_utc_time,
    write_markdown_run_summary,
    write_run_summary,
)
from src.skill_extraction.groq_extractor import extract_skills_with_groq


DEFAULT_INPUT_PATH = ROOT_DIR / "data" / "raw" / "canada_jobs.csv"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "canada_jobs_snapshot.csv"


def load_existing_extractions(path: Path) -> dict[str, dict[str, object]]:
    """Load successful prior rows so interrupted builds can resume cheaply."""
    if not path.exists():
        return {}

    existing_df = pd.read_csv(path)

    if "job_id" not in existing_df.columns:
        return {}

    return {
        str(row["job_id"]): row.to_dict()
        for _, row in existing_df.iterrows()
        if str(row.get("skills_text", "")).strip()
    }


def extract_skills_groq_first(
    *,
    title: str,
    description: str,
    max_attempts: int = 2,
    retry_delay_seconds: int = 3,
) -> tuple[list[str], str, str]:
    """Use Groq for complete descriptions, with deterministic emergency fallback."""
    errors: list[str] = []

    for attempt in range(1, max_attempts + 1):
        try:
            result = extract_skills_with_groq(
                title=title,
                description=description,
            )

            if result.skills:
                return result.skills, "groq", ""

            errors.append(f"Groq attempt {attempt}: returned no skills")
        except Exception as error:
            errors.append(
                f"Groq attempt {attempt}: {type(error).__name__}: {error}"
            )

        if attempt < max_attempts:
            time.sleep(retry_delay_seconds)

    fallback_skills = extract_skills_deterministic(description)
    return fallback_skills, "deterministic_fallback", " | ".join(errors)


def process_selected_jobs(
    jobs: list[dict[str, object]],
    *,
    existing_rows: dict[str, dict[str, object]] | None = None,
    delay_seconds: float = 1,
    checkpoint_path: Path | None = None,
) -> list[dict[str, object]]:
    """Groq-enrich selected jobs and preserve resumable completed rows."""
    existing_rows = existing_rows or {}
    processed_rows: list[dict[str, object]] = []

    for index, job in enumerate(jobs, start=1):
        job_id = str(job.get("job_id", ""))
        title = str(job.get("title", ""))
        description = str(job.get("description", ""))
        clean_title = normalize_text(title)
        clean_description = normalize_text(description)

        if job_id in existing_rows:
            existing_row = existing_rows[job_id]
            existing_clean_description = str(
                existing_row.get("clean_description", "")
            ).strip()

            if existing_clean_description == clean_description:
                processed_rows.append(
                    {
                        **job,
                        "clean_title": clean_title,
                        "clean_description": clean_description,
                        "extracted_skills": existing_row.get(
                            "extracted_skills",
                            [],
                        ),
                        "skills_text": existing_row.get("skills_text", ""),
                        "skill_extraction_provider": existing_row.get(
                            "skill_extraction_provider",
                            "groq",
                        ),
                        "skill_extraction_error": existing_row.get(
                            "skill_extraction_error",
                            "",
                        ),
                    }
                )
                print(f"[{index}/{len(jobs)}] Reused {job.get('title')}")
                continue

            print(
                f"[{index}/{len(jobs)}] Description changed; "
                f"re-extracting {job.get('title')}"
            )

        print(f"[{index}/{len(jobs)}] Extracting {title} at {job.get('company')}")

        skills, provider, extraction_error = extract_skills_groq_first(
            title=title,
            description=description,
        )

        if not skills:
            print("  Skipped because no technical skills were extracted.")
            continue

        processed_rows.append(
            {
                **job,
                "clean_title": clean_title,
                "clean_description": clean_description,
                "extracted_skills": skills,
                "skills_text": ", ".join(skills),
                "role_category": categorize_role(title, description),
                "skill_extraction_provider": provider,
                "skill_extraction_error": extraction_error,
            }
        )

        if checkpoint_path is not None:
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(processed_rows).to_csv(checkpoint_path, index=False)

        time.sleep(delay_seconds)

    return processed_rows


def build_snapshot_run_summary(
    *,
    selected_jobs: list[dict[str, object]],
    processed_rows: list[dict[str, object]],
    started_at: datetime,
    output_path: Path,
) -> IngestionRunSummary:
    provider_counts = Counter(
        str(row.get("skill_extraction_provider", "")).strip() or "unknown"
        for row in processed_rows
    )
    extraction_errors = [
        f"{row.get('job_id', 'unknown')}: {row.get('skill_extraction_error')}"
        for row in processed_rows
        if str(row.get("skill_extraction_error", "")).strip()
    ]
    skipped_count = max(0, len(selected_jobs) - len(processed_rows))

    if skipped_count:
        extraction_errors.append(
            f"{skipped_count} selected postings were skipped during enrichment."
        )

    return build_single_stage_run_summary(
        source_type="canada_snapshot_enrichment",
        started_at=started_at,
        completed_at=current_utc_time(),
        raw_job_count=len(selected_jobs),
        processed_job_count=len(processed_rows),
        errors=extraction_errors,
        metadata={
            "output_path": str(output_path),
            "provider_counts": dict(provider_counts),
            "skipped_count": skipped_count,
        },
    )


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
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    max_jobs: int = 72,
    max_per_company: int = 6,
    max_per_location: int = 18,
    delay_seconds: float = 1,
    summary_path: Path | None = None,
    summary_markdown_path: Path | None = None,
    save_run_to_db: bool = False,
    dataset_name: str | None = "canada_jobs",
) -> None:
    started_at = current_utc_time()
    raw_jobs_df = pd.read_csv(input_path)
    candidates = raw_jobs_df.to_dict(orient="records")
    selected_jobs = select_balanced_jobs(
        candidates,
        max_jobs=max_jobs,
        max_per_company=max_per_company,
        max_per_location=max_per_location,
    )
    existing_rows = load_existing_extractions(output_path)
    processed_rows = process_selected_jobs(
        selected_jobs,
        existing_rows=existing_rows,
        delay_seconds=delay_seconds,
        checkpoint_path=output_path,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(processed_rows).to_csv(output_path, index=False)
    summary = build_snapshot_run_summary(
        selected_jobs=selected_jobs,
        processed_rows=processed_rows,
        started_at=started_at,
        output_path=output_path,
    )

    if summary_path is not None:
        write_run_summary(summary, summary_path)

    if summary_markdown_path is not None:
        write_markdown_run_summary(summary, summary_markdown_path)

    if save_run_to_db:
        save_run_summary_to_database(summary, dataset_name=dataset_name)

    print(f"\nSelected {len(selected_jobs)} balanced Canadian postings.")
    print(f"Saved {len(processed_rows)} enriched postings to {output_path}.")
    print()
    print(build_markdown_run_summary(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the Groq-enriched Canada jobs dashboard snapshot."
    )
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--max-jobs", type=int, default=72)
    parser.add_argument("--max-per-company", type=int, default=6)
    parser.add_argument("--max-per-location", type=int, default=18)
    parser.add_argument("--delay-seconds", type=float, default=1)
    parser.add_argument("--summary-path", type=Path)
    parser.add_argument("--summary-markdown-path", type=Path)
    parser.add_argument("--save-run-to-db", action="store_true")
    parser.add_argument("--dataset-name", default="canada_jobs")
    arguments = parser.parse_args()

    main(
        input_path=arguments.input_path,
        output_path=arguments.output_path,
        max_jobs=arguments.max_jobs,
        max_per_company=arguments.max_per_company,
        max_per_location=arguments.max_per_location,
        delay_seconds=arguments.delay_seconds,
        summary_path=arguments.summary_path,
        summary_markdown_path=arguments.summary_markdown_path,
        save_run_to_db=arguments.save_run_to_db,
        dataset_name=arguments.dataset_name,
    )
