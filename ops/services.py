from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from src.database.db import get_db_session
from src.database.models import (
    ExtractionResult,
    IngestionRun,
    JobPosting,
    JobSkill,
    ProcessedJob,
    Skill,
)


DEFAULT_RECENT_RUN_LIMIT = 20
DEFAULT_SKILL_LIMIT = 15
DEFAULT_EMPTY_EXTRACTION_LIMIT = 25


def normalize_source(value: object) -> str:
    source = str(value or "").strip()
    return source if source else "unknown"


def coerce_run_metadata(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def duration_seconds(
    started_at: datetime | None,
    completed_at: datetime | None,
) -> float | None:
    if started_at is None or completed_at is None:
        return None

    return max(0.0, (completed_at - started_at).total_seconds())


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "In progress"

    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = seconds / 60
    return f"{minutes:.1f}m"


def load_dashboard_inputs() -> dict[str, Any]:
    with get_db_session() as session:
        source_counts = [
            {
                "source": normalize_source(row.source),
                "count": int(row.count),
            }
            for row in session.execute(
                select(
                    JobPosting.source.label("source"),
                    func.count(JobPosting.id).label("count"),
                )
                .group_by(JobPosting.source)
                .order_by(func.count(JobPosting.id).desc())
            ).all()
        ]
        total_postings = int(
            session.execute(select(func.count(JobPosting.id))).scalar_one()
        )
        recent_runs = [
            ingestion_run_to_dict(run)
            for run in session.execute(
                select(IngestionRun)
                .order_by(IngestionRun.started_at.desc())
                .limit(DEFAULT_RECENT_RUN_LIMIT)
            ).scalars()
        ]

    return {
        "source_counts": source_counts,
        "total_postings": total_postings,
        "recent_runs": recent_runs,
    }


def ingestion_run_to_dict(run: IngestionRun) -> dict[str, Any]:
    metadata = coerce_run_metadata(getattr(run, "run_metadata", {}))
    seconds = duration_seconds(run.started_at, run.completed_at)

    return {
        "id": run.id,
        "source_type": run.source_type,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "duration_seconds": seconds,
        "duration_label": format_duration(seconds),
        "raw_job_count": run.raw_job_count,
        "processed_job_count": run.processed_job_count,
        "total_sources": run.total_sources,
        "successful_sources": run.successful_sources,
        "failed_sources": run.failed_sources,
        "error_log": run.error_log or [],
        "run_metadata": metadata,
        "source_results": metadata.get("source_results", []),
    }


def latest_ingestion_timestamp(recent_runs: list[dict[str, Any]]) -> datetime | None:
    if not recent_runs:
        return None

    latest_run = recent_runs[0]
    return latest_run.get("completed_at") or latest_run.get("started_at")


def latest_dedup_rejected_count(recent_runs: list[dict[str, Any]]) -> int:
    for run in recent_runs:
        metadata = coerce_run_metadata(run.get("run_metadata"))
        if "dedup_rejected_count" in metadata:
            return int(metadata.get("dedup_rejected_count") or 0)

    return 0


def build_dashboard_context(inputs: dict[str, Any]) -> dict[str, Any]:
    source_counts = inputs.get("source_counts", [])
    recent_runs = inputs.get("recent_runs", [])

    return {
        "source_counts": source_counts,
        "total_postings": int(inputs.get("total_postings") or 0),
        "last_ingestion_timestamp": latest_ingestion_timestamp(recent_runs),
        "dedup_rejected_count": latest_dedup_rejected_count(recent_runs),
        "recent_runs": recent_runs[:5],
    }


def get_dashboard_context() -> dict[str, Any]:
    return build_dashboard_context(load_dashboard_inputs())


def load_recent_ingestion_runs(limit: int = DEFAULT_RECENT_RUN_LIMIT) -> list[dict[str, Any]]:
    with get_db_session() as session:
        runs = session.execute(
            select(IngestionRun)
            .order_by(IngestionRun.started_at.desc())
            .limit(limit)
        ).scalars()

        return [ingestion_run_to_dict(run) for run in runs]


def build_ingestion_runs_context(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"runs": runs}


def get_ingestion_runs_context() -> dict[str, Any]:
    return build_ingestion_runs_context(load_recent_ingestion_runs())


def load_extraction_health_inputs() -> dict[str, Any]:
    with get_db_session() as session:
        top_skills = [
            {
                "skill": row.skill,
                "count": int(row.count),
            }
            for row in session.execute(
                select(
                    Skill.name.label("skill"),
                    func.count(JobSkill.id).label("count"),
                )
                .join(JobSkill, JobSkill.skill_id == Skill.id)
                .group_by(Skill.id, Skill.name)
                .order_by(func.count(JobSkill.id).desc(), Skill.name.asc())
                .limit(DEFAULT_SKILL_LIMIT)
            ).all()
        ]

        empty_extractions = [
            {
                "title": row.title,
                "company": row.company,
                "source": normalize_source(row.source),
                "source_url": row.source_url,
                "provider": row.provider,
                "error": row.error,
                "created_at": row.created_at,
            }
            for row in session.execute(
                select(
                    JobPosting.title,
                    JobPosting.company,
                    JobPosting.source,
                    JobPosting.source_url,
                    ExtractionResult.provider,
                    ExtractionResult.error,
                    ExtractionResult.created_at,
                )
                .join(ProcessedJob, ProcessedJob.job_posting_id == JobPosting.id)
                .join(
                    ExtractionResult,
                    ExtractionResult.processed_job_id == ProcessedJob.id,
                )
                .where(ExtractionResult.extracted_skills == [])
                .order_by(ExtractionResult.created_at.desc())
                .limit(DEFAULT_EMPTY_EXTRACTION_LIMIT)
            ).all()
        ]

    return {
        "top_skills": top_skills,
        "empty_extractions": empty_extractions,
    }


def build_extraction_health_context(inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "top_skills": inputs.get("top_skills", []),
        "empty_extractions": inputs.get("empty_extractions", []),
    }


def get_extraction_health_context() -> dict[str, Any]:
    return build_extraction_health_context(load_extraction_health_inputs())

