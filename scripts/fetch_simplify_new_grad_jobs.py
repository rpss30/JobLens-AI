"""Fetch and normalize Simplify new-grad job listings."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.ingestion.canada_jobs import (
    TARGET_ROLE_CATEGORIES,
    is_target_technical_job,
    prepare_canada_jobs_with_metrics,
)
from src.ingestion.pipeline_runs import (
    build_markdown_run_summary,
    build_single_stage_run_summary,
    current_utc_time,
    validate_job_records,
    write_markdown_run_summary,
    write_run_summary,
)
from src.ingestion.simplify_new_grad import (
    DEFAULT_SIMPLIFY_NEW_GRAD_README_URL,
    SIMPLIFY_SOURCE,
    fetch_simplify_new_grad_postings,
    normalize_simplify_new_grad_postings,
)


DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "raw" / "simplify_new_grad_jobs.csv"


def is_target_joblens_role(job: dict[str, object]) -> bool:
    """Return whether a normalized row belongs to JobLens target categories."""
    return (
        is_target_technical_job(job)
        and str(job.get("role_category", "")) in TARGET_ROLE_CATEGORIES
    )


def prepare_simplify_new_grad_jobs(
    jobs: list[dict[str, object]],
    *,
    target_roles_only: bool = True,
    canada_only: bool = False,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Filter normalized Simplify rows for the requested artifact."""
    filtered_jobs = [
        job
        for job in jobs
        if not target_roles_only or is_target_joblens_role(job)
    ]

    if not canada_only:
        return filtered_jobs, {
            "target_role_rejected_count": len(jobs) - len(filtered_jobs),
            "dedup_rejected_count": 0,
        }

    canada_jobs, canada_metrics = prepare_canada_jobs_with_metrics(filtered_jobs)

    return canada_jobs, {
        "target_role_rejected_count": len(jobs) - len(filtered_jobs),
        **canada_metrics,
    }


def main(
    *,
    readme_url: str = DEFAULT_SIMPLIFY_NEW_GRAD_README_URL,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    summary_path: Path | None = None,
    summary_markdown_path: Path | None = None,
    target_roles_only: bool = True,
    canada_only: bool = False,
) -> None:
    started_at = current_utc_time()
    postings = fetch_simplify_new_grad_postings(readme_url)
    normalized_jobs = normalize_simplify_new_grad_postings(
        postings,
        fetched_at=started_at,
    )
    prepared_jobs, pipeline_metrics = prepare_simplify_new_grad_jobs(
        normalized_jobs,
        target_roles_only=target_roles_only,
        canada_only=canada_only,
    )
    validation_errors = validate_job_records(prepared_jobs)
    summary = build_single_stage_run_summary(
        source_type="simplify_new_grad_fetch",
        started_at=started_at,
        completed_at=current_utc_time(),
        raw_job_count=len(postings),
        processed_job_count=len(prepared_jobs),
        errors=validation_errors,
        metadata={
            "readme_url": readme_url,
            "output_path": str(output_path),
            "source": SIMPLIFY_SOURCE,
            "target_roles_only": target_roles_only,
            "canada_only": canada_only,
            "location_scope": "canada" if canada_only else "global",
            **pipeline_metrics,
        },
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(prepared_jobs).to_csv(output_path, index=False)

    if summary_path is not None:
        write_run_summary(summary, summary_path)

    if summary_markdown_path is not None:
        write_markdown_run_summary(summary, summary_markdown_path)

    print(f"\nFetched {len(postings)} active Simplify new-grad postings.")
    scope_label = "Canada-only" if canada_only else "global"
    print(
        f"Saved {len(prepared_jobs)} {scope_label} normalized postings "
        f"to {output_path}."
    )
    print()
    print(build_markdown_run_summary(summary))

    if validation_errors:
        formatted_errors = "\n".join(f"- {error}" for error in validation_errors)
        raise ValueError(
            f"Simplify new-grad fetch validation failed:\n{formatted_errors}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Fetch global new-grad jobs from Simplify's public index. "
            "Use --canada-only only when testing Canada snapshot compatibility."
        )
    )
    parser.add_argument(
        "--readme-url",
        default=DEFAULT_SIMPLIFY_NEW_GRAD_README_URL,
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )
    parser.add_argument("--summary-path", type=Path)
    parser.add_argument("--summary-markdown-path", type=Path)
    parser.add_argument(
        "--include-non-target-roles",
        action="store_true",
        help="Keep rows outside JobLens target technical role categories.",
    )
    parser.add_argument(
        "--canada-only",
        action="store_true",
        help="Keep only rows that can be normalized as Canadian roles.",
    )
    arguments = parser.parse_args()

    main(
        readme_url=arguments.readme_url,
        output_path=arguments.output_path,
        summary_path=arguments.summary_path,
        summary_markdown_path=arguments.summary_markdown_path,
        target_roles_only=not arguments.include_non_target_roles,
        canada_only=arguments.canada_only,
    )
