"""Pipeline run summaries and validation helpers for ingestion refreshes."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


SUCCESS_STATUS = "succeeded"
PARTIAL_SUCCESS_STATUS = "partial_success"
FAILED_STATUS = "failed"

REQUIRED_NORMALIZED_JOB_FIELDS = {
    "job_id",
    "title",
    "company",
    "location",
    "description",
    "source",
    "source_url",
    "fetched_at",
    "role_category",
}


def current_utc_time() -> datetime:
    return datetime.now(UTC)


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


@dataclass(frozen=True)
class SourceFetchResult:
    company: str
    source_type: str
    source_identifier: str
    status: str
    job_count: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "company": self.company,
            "source_type": self.source_type,
            "source_identifier": self.source_identifier,
            "status": self.status,
            "job_count": self.job_count,
            "error": self.error,
        }


@dataclass(frozen=True)
class IngestionRunSummary:
    source_type: str
    status: str
    started_at: datetime
    completed_at: datetime
    total_sources: int
    successful_sources: int
    failed_sources: int
    raw_job_count: int
    processed_job_count: int
    error_log: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return max(
            0.0,
            (self.completed_at - self.started_at).total_seconds(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "source_type": self.source_type,
            "status": self.status,
            "started_at": serialize_datetime(self.started_at),
            "completed_at": serialize_datetime(self.completed_at),
            "duration_seconds": self.duration_seconds,
            "total_sources": self.total_sources,
            "successful_sources": self.successful_sources,
            "failed_sources": self.failed_sources,
            "raw_job_count": self.raw_job_count,
            "processed_job_count": self.processed_job_count,
            "error_log": self.error_log,
            "metadata": self.metadata,
        }


def determine_run_status(
    *,
    successful_sources: int,
    failed_sources: int,
    processed_job_count: int,
) -> str:
    if processed_job_count <= 0 or successful_sources <= 0:
        return FAILED_STATUS

    if failed_sources > 0:
        return PARTIAL_SUCCESS_STATUS

    return SUCCESS_STATUS


def build_ingestion_run_summary(
    *,
    source_type: str,
    started_at: datetime,
    completed_at: datetime | None = None,
    source_results: Iterable[SourceFetchResult],
    raw_job_count: int,
    processed_job_count: int,
    metadata: dict[str, Any] | None = None,
) -> IngestionRunSummary:
    completed_time = completed_at or current_utc_time()
    source_results_list = list(source_results)
    successful_sources = sum(
        1 for result in source_results_list if result.status == SUCCESS_STATUS
    )
    failed_sources = sum(
        1 for result in source_results_list if result.status == FAILED_STATUS
    )
    error_log = [
        f"{result.company}: {result.error}"
        for result in source_results_list
        if result.error
    ]

    return IngestionRunSummary(
        source_type=source_type,
        status=determine_run_status(
            successful_sources=successful_sources,
            failed_sources=failed_sources,
            processed_job_count=processed_job_count,
        ),
        started_at=started_at,
        completed_at=completed_time,
        total_sources=len(source_results_list),
        successful_sources=successful_sources,
        failed_sources=failed_sources,
        raw_job_count=raw_job_count,
        processed_job_count=processed_job_count,
        error_log=error_log,
        metadata={
            **(metadata or {}),
            "source_results": [
                result.to_dict() for result in source_results_list
            ],
        },
    )


def build_single_stage_run_summary(
    *,
    source_type: str,
    started_at: datetime,
    completed_at: datetime | None = None,
    raw_job_count: int,
    processed_job_count: int,
    errors: Iterable[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> IngestionRunSummary:
    error_log = [error for error in errors or [] if error]
    successful_sources = 1 if processed_job_count > 0 else 0
    failed_sources = 1 if processed_job_count <= 0 or error_log else 0

    return IngestionRunSummary(
        source_type=source_type,
        status=determine_run_status(
            successful_sources=successful_sources,
            failed_sources=failed_sources,
            processed_job_count=processed_job_count,
        ),
        started_at=started_at,
        completed_at=completed_at or current_utc_time(),
        total_sources=1,
        successful_sources=successful_sources,
        failed_sources=failed_sources,
        raw_job_count=raw_job_count,
        processed_job_count=processed_job_count,
        error_log=error_log,
        metadata=metadata or {},
    )


def validate_job_records(
    jobs: Iterable[dict[str, object]],
    *,
    required_fields: set[str] | None = None,
    unique_fields: tuple[str, ...] = ("job_id", "source_url"),
) -> list[str]:
    """Return data quality errors for normalized ingestion records."""
    required = required_fields or REQUIRED_NORMALIZED_JOB_FIELDS
    jobs_list = list(jobs)
    errors: list[str] = []

    if not jobs_list:
        return ["No normalized jobs were produced."]

    for index, job in enumerate(jobs_list, start=1):
        missing_fields = [
            field_name
            for field_name in sorted(required)
            if not str(job.get(field_name, "")).strip()
        ]

        if missing_fields:
            errors.append(
                f"Job {index} is missing required fields: "
                f"{', '.join(missing_fields)}."
            )

    for field_name in unique_fields:
        values = [
            str(job.get(field_name, "")).strip()
            for job in jobs_list
            if str(job.get(field_name, "")).strip()
        ]
        duplicates = sorted(
            value for value, count in Counter(values).items() if count > 1
        )

        if duplicates:
            preview = ", ".join(duplicates[:5])
            errors.append(f"Duplicate {field_name} values found: {preview}.")

    return errors


def build_markdown_run_summary(summary: IngestionRunSummary) -> str:
    lines = [
        f"## {summary.source_type.replace('_', ' ').title()} Run",
        "",
        f"- Status: **{summary.status}**",
        f"- Duration: **{summary.duration_seconds:.1f}s**",
        f"- Sources: **{summary.successful_sources}/{summary.total_sources}** successful",
        f"- Raw jobs: **{summary.raw_job_count}**",
        f"- Processed jobs: **{summary.processed_job_count}**",
    ]

    if summary.failed_sources:
        lines.append(f"- Failed sources: **{summary.failed_sources}**")

    if summary.error_log:
        lines.extend(["", "### Errors"])
        lines.extend(f"- {error}" for error in summary.error_log)

    return "\n".join(lines) + "\n"


def write_run_summary(summary: IngestionRunSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def write_markdown_run_summary(
    summary: IngestionRunSummary,
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown_run_summary(summary), encoding="utf-8")
