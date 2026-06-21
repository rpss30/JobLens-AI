"""Client for fetching public Ashby job postings."""

from __future__ import annotations

from typing import Any

import requests

from src.ingestion.ats_normalizers import (
    build_ats_job_id,
    clean_html_text,
    current_utc_timestamp,
    infer_experience_level_from_text,
)


ASHBY_POSTINGS_URL = (
    "https://api.ashbyhq.com/posting-api/job-board/{job_board_name}"
)


def fetch_ashby_postings(
    job_board_name: str,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    """Fetch currently published postings for one Ashby job board."""
    cleaned_board_name = job_board_name.strip()

    if not cleaned_board_name:
        raise ValueError("job_board_name cannot be empty.")

    response = requests.get(
        ASHBY_POSTINGS_URL.format(job_board_name=cleaned_board_name),
        params={"includeCompensation": "true"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    payload = response.json()
    jobs = payload.get("jobs")

    if not isinstance(jobs, list):
        raise ValueError("Ashby API response must contain a 'jobs' list.")

    return jobs


def get_primary_ashby_address(posting: dict[str, Any]) -> dict[str, Any]:
    """Return the primary structured postal address when available."""
    address_data = posting.get("address") or {}
    postal_address = address_data.get("postalAddress") or {}

    if isinstance(postal_address, dict):
        return postal_address

    return {}


def normalize_ashby_posting(
    posting: dict[str, Any],
    *,
    company_name: str,
    job_board_name: str,
    fetched_at: str | None = None,
) -> dict[str, object]:
    """Normalize one Ashby posting into the extended JobLens raw schema."""
    job_url = clean_html_text(posting.get("jobUrl"))
    posting_id = posting.get("id") or job_url or posting.get("title", "")
    title = clean_html_text(posting.get("title"))
    description = clean_html_text(
        posting.get("descriptionPlain") or posting.get("descriptionHtml")
    )
    primary_address = get_primary_ashby_address(posting)

    return {
        "job_id": build_ats_job_id("ashby", job_board_name, posting_id),
        "title": title,
        "company": company_name,
        "location": clean_html_text(posting.get("location")),
        "description": description,
        "experience_level": infer_experience_level_from_text(title, description),
        "source": "ashby",
        "source_url": job_url or clean_html_text(posting.get("applyUrl")),
        "fetched_at": fetched_at or current_utc_timestamp(),
        "date_posted": clean_html_text(posting.get("publishedAt")),
        "valid_through": "",
        "employment_type": clean_html_text(posting.get("employmentType")),
        "workplace_type": clean_html_text(posting.get("workplaceType")),
        "is_remote": bool(posting.get("isRemote")),
        "address_locality": clean_html_text(
            primary_address.get("addressLocality")
        ),
        "address_region": clean_html_text(
            primary_address.get("addressRegion")
        ),
        "address_country": clean_html_text(
            primary_address.get("addressCountry")
        ),
    }
