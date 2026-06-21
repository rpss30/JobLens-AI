"""Client for fetching public Lever job postings."""

from __future__ import annotations

from typing import Any

import requests

from src.ingestion.ats_normalizers import (
    build_ats_job_id,
    clean_html_text,
    current_utc_timestamp,
    epoch_milliseconds_to_iso,
    infer_experience_level_from_text,
)


LEVER_POSTINGS_URL = "https://api.lever.co/v0/postings/{company_slug}"


def fetch_lever_postings(
    company_slug: str,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    """Fetch public job postings for one Lever-hosted company."""
    cleaned_company_slug = company_slug.strip().lower()

    if not cleaned_company_slug:
        raise ValueError("company_slug cannot be empty.")

    response = requests.get(
        LEVER_POSTINGS_URL.format(company_slug=cleaned_company_slug),
        params={"mode": "json"},
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, list):
        raise ValueError("Lever API response must be a list of postings.")

    return payload

def normalize_lever_posting(
    posting: dict[str, Any],
    company_slug: str,
    fetched_at: str | None = None,
) -> dict[str, object]:
    """Normalize one Lever posting into the JobLens raw job schema."""
    posting_id = posting.get("id") or posting.get("hostedUrl") or posting.get("text", "")
    title = clean_html_text(posting.get("text"))
    company = clean_html_text(posting.get("categories", {}).get("team")) or company_slug
    location = clean_html_text(posting.get("categories", {}).get("location"))

    description_parts = [
        posting.get("description"),
        posting.get("descriptionPlain"),
        posting.get("descriptionHtml"),
        posting.get("additional"),
        posting.get("lists"),
    ]

    description_text_parts: list[str] = []

    for part in description_parts:
        if isinstance(part, list):
            for item in part:
                if isinstance(item, dict):
                    description_text_parts.append(clean_html_text(item.get("text", "")))
                    for content in item.get("content", []):
                        description_text_parts.append(clean_html_text(content))
                else:
                    description_text_parts.append(clean_html_text(item))
        else:
            description_text_parts.append(clean_html_text(part))

    description = clean_html_text(" ".join(description_text_parts))
    workplace_type = clean_html_text(
        posting.get("workplaceType")
        or posting.get("categories", {}).get("commitment")
    )

    return {
        "job_id": build_ats_job_id("lever", company_slug, posting_id),
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "experience_level": infer_experience_level_from_text(title, description),
        "source": "lever",
        "source_url": posting.get("hostedUrl", ""),
        "fetched_at": fetched_at or current_utc_timestamp(),
        "date_posted": epoch_milliseconds_to_iso(posting.get("createdAt")),
        "valid_through": "",
        "employment_type": clean_html_text(
            posting.get("categories", {}).get("commitment")
        ),
        "workplace_type": workplace_type,
        "is_remote": (
            "remote" in location.lower()
            or "remote" in workplace_type.lower()
        ),
        "address_locality": "",
        "address_region": "",
        "address_country": "",
        "source_updated_at": epoch_milliseconds_to_iso(
            posting.get("updatedAt")
        ),
    }
