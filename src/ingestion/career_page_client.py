"""Extract Schema.org JobPosting data from first-party career pages."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from typing import Any, Iterator

import requests

from src.ingestion.ats_normalizers import (
    build_ats_job_id,
    clean_html_text,
    current_utc_timestamp,
    infer_experience_level_from_text,
)


class JsonLdScriptParser(HTMLParser):
    """Collect JSON-LD script contents from an HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self._collecting = False
        self._chunks: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {name.lower(): value for name, value in attrs}
        script_type = (attributes.get("type") or "").lower()

        if tag.lower() == "script" and script_type == "application/ld+json":
            self._collecting = True
            self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._collecting:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._collecting:
            self.scripts.append("".join(self._chunks).strip())
            self._collecting = False
            self._chunks = []


def iter_job_postings(value: object) -> Iterator[dict[str, Any]]:
    """Yield JobPosting objects from nested JSON-LD structures."""
    if isinstance(value, list):
        for item in value:
            yield from iter_job_postings(item)
        return

    if not isinstance(value, dict):
        return

    raw_type = value.get("@type")
    types = raw_type if isinstance(raw_type, list) else [raw_type]

    if "JobPosting" in types:
        yield value

    for child_value in value.values():
        if isinstance(child_value, (dict, list)):
            yield from iter_job_postings(child_value)


def extract_job_postings_from_html(html: str) -> list[dict[str, Any]]:
    """Parse all valid JobPosting JSON-LD objects from HTML."""
    parser = JsonLdScriptParser()
    parser.feed(html)
    postings: list[dict[str, Any]] = []

    for script_text in parser.scripts:
        if not script_text:
            continue

        try:
            payload = json.loads(script_text)
        except json.JSONDecodeError:
            continue

        postings.extend(iter_job_postings(payload))

    return postings


def fetch_career_page_postings(
    careers_url: str,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    """Fetch a careers page and return embedded JobPosting objects."""
    response = requests.get(
        careers_url,
        timeout=timeout_seconds,
        headers={"User-Agent": "JobLensAI/1.0 portfolio ingestion"},
    )
    response.raise_for_status()
    return extract_job_postings_from_html(response.text)


def get_nested_value(value: object, *keys: str) -> object:
    """Read a nested dictionary value without assuming every level exists."""
    current = value

    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)

    return current or ""


def get_job_location(posting: dict[str, Any]) -> dict[str, object]:
    """Return normalized structured fields from the first listed job location."""
    location_data = posting.get("jobLocation")

    if isinstance(location_data, list):
        location_data = location_data[0] if location_data else {}

    if not isinstance(location_data, dict):
        location_data = {}

    address = location_data.get("address") or {}
    if not isinstance(address, dict):
        address = {}

    locality = clean_html_text(address.get("addressLocality"))
    region = clean_html_text(address.get("addressRegion"))
    country = clean_html_text(address.get("addressCountry"))
    location = ", ".join(
        part for part in (locality, region, country) if part
    )

    return {
        "location": location,
        "address_locality": locality,
        "address_region": region,
        "address_country": country,
    }


def applicant_country_text(posting: dict[str, Any]) -> str:
    """Return remote applicant location requirements as searchable text."""
    requirements = posting.get("applicantLocationRequirements")

    if not isinstance(requirements, list):
        requirements = [requirements] if requirements else []

    return " ".join(
        clean_html_text(
            requirement.get("name")
            if isinstance(requirement, dict)
            else requirement
        )
        for requirement in requirements
    ).strip()


def normalize_jsonld_posting(
    posting: dict[str, Any],
    *,
    company_fallback: str,
    source_page_url: str,
    fetched_at: str | None = None,
) -> dict[str, object]:
    """Normalize one Schema.org JobPosting into the extended JobLens schema."""
    title = clean_html_text(posting.get("title"))
    description = clean_html_text(posting.get("description"))
    organization_name = clean_html_text(
        get_nested_value(posting, "hiringOrganization", "name")
    )
    identifier = posting.get("identifier")

    if isinstance(identifier, dict):
        posting_id = identifier.get("value") or identifier.get("name")
    else:
        posting_id = identifier

    source_url = clean_html_text(posting.get("url")) or source_page_url
    posting_id = posting_id or source_url or title
    location_fields = get_job_location(posting)
    remote_country = applicant_country_text(posting)
    is_remote = clean_html_text(posting.get("jobLocationType")).upper() == "TELECOMMUTE"
    location = str(location_fields["location"])

    if is_remote and remote_country:
        location = f"Remote, {remote_country}"

    return {
        "job_id": build_ats_job_id(
            "jsonld",
            company_fallback,
            posting_id,
        ),
        "title": title,
        "company": organization_name or company_fallback,
        "location": location,
        "description": description,
        "experience_level": infer_experience_level_from_text(title, description),
        "source": "jsonld",
        "source_url": source_url,
        "fetched_at": fetched_at or current_utc_timestamp(),
        "date_posted": clean_html_text(posting.get("datePosted")),
        "valid_through": clean_html_text(posting.get("validThrough")),
        "employment_type": clean_html_text(posting.get("employmentType")),
        "workplace_type": "Remote" if is_remote else "",
        "is_remote": is_remote,
        "address_locality": location_fields["address_locality"],
        "address_region": location_fields["address_region"],
        "address_country": location_fields["address_country"],
    }
