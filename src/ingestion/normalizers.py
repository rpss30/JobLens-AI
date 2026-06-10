"""Helpers for normalizing external job API results into JobLens raw schema."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


RAW_JOB_COLUMNS = [
    "job_id",
    "title",
    "company",
    "location",
    "description",
    "experience_level",
    "source",
    "source_url",
    "fetched_at",
]


def _safe_get_nested(data: dict[str, Any], *keys: str) -> str:
    """Safely read a nested string value from a dictionary."""
    current: Any = data

    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)

    if current is None:
        return ""

    return str(current).strip()


def infer_experience_level(title: str, description: str) -> str:
    """Infer a simple experience level label from title and description text."""
    text = f"{title} {description}".lower()

    entry_keywords = [
        "intern",
        "internship",
        "junior",
        "entry level",
        "new grad",
        "graduate",
        "co-op",
        "coop",
    ]

    senior_keywords = [
        "senior",
        "staff",
        "principal",
        "lead",
        "manager",
        "architect",
        "director",
    ]

    if any(keyword in text for keyword in entry_keywords):
        return "Entry Level"

    if any(keyword in text for keyword in senior_keywords):
        return "Senior"

    return "Mid Level"


def normalize_adzuna_job(job: dict[str, Any]) -> dict[str, str]:
    """Normalize one Adzuna job result into the JobLens raw job schema."""
    title = str(job.get("title") or "").strip()
    description = str(job.get("description") or "").strip()

    company = _safe_get_nested(job, "company", "display_name")
    location = _safe_get_nested(job, "location", "display_name")

    return {
        "job_id": str(job.get("id") or "").strip(),
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "experience_level": infer_experience_level(title, description),
        "source": "adzuna",
        "source_url": str(job.get("redirect_url") or "").strip(),
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def normalize_adzuna_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Normalize a list of Adzuna job results."""
    normalized_jobs = [normalize_adzuna_job(job) for job in jobs]

    return [
        job
        for job in normalized_jobs
        if job["title"] and job["company"] and job["location"] and job["description"]
    ]