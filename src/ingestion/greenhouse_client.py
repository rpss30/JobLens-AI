"""Client for fetching public Greenhouse job postings."""

from __future__ import annotations

from typing import Any

import requests

from src.ingestion.ats_normalizers import (
    build_ats_job_id,
    clean_html_text,
    current_utc_timestamp,
    infer_experience_level_from_text,
)


GREENHOUSE_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"


def fetch_greenhouse_jobs(
    company_slug: str,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    """Fetch public job postings for one Greenhouse-hosted company."""
    cleaned_company_slug = company_slug.strip().lower()

    if not cleaned_company_slug:
        raise ValueError("company_slug cannot be empty.")

    response = requests.get(
        GREENHOUSE_JOBS_URL.format(company_slug=cleaned_company_slug),
        params={"content": "true"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    payload = response.json()

    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("Greenhouse API response must contain a 'jobs' list.")

    return jobs


def normalize_greenhouse_job(
    job: dict[str, Any],
    company_slug: str,
    fetched_at: str | None = None,
) -> dict[str, object]:
    """Normalize one Greenhouse job into the JobLens raw job schema."""
    job_id = job.get("id") or job.get("absolute_url") or job.get("title", "")
    title = clean_html_text(job.get("title"))
    company = company_slug

    location_data = job.get("location") or {}
    location = clean_html_text(location_data.get("name"))

    content = clean_html_text(job.get("content"))
    departments = job.get("departments") or []
    offices = job.get("offices") or []

    department_names = [
        clean_html_text(department.get("name"))
        for department in departments
        if isinstance(department, dict)
    ]
    office_names = [
        clean_html_text(office.get("name"))
        for office in offices
        if isinstance(office, dict)
    ]

    description_parts = [
        content,
        " ".join(department_names),
        " ".join(office_names),
    ]
    description = clean_html_text(" ".join(description_parts))

    return {
        "job_id": build_ats_job_id("greenhouse", company_slug, job_id),
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "experience_level": infer_experience_level_from_text(title, description),
        "source": "greenhouse",
        "source_url": job.get("absolute_url", ""),
        "fetched_at": fetched_at or current_utc_timestamp(),
        "date_posted": "",
        "valid_through": "",
        "employment_type": "",
        "workplace_type": "",
        "is_remote": "remote" in location.lower(),
        "address_locality": "",
        "address_region": "",
        "address_country": "",
        "source_updated_at": clean_html_text(job.get("updated_at")),
    }
