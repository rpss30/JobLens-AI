"""Shared filtering, deduplication, and selection for Canada job snapshots."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
from typing import Iterable

from src.ingestion.canada_locations import normalize_canadian_location
from src.processing.job_processor import categorize_role


TARGET_TITLE_TERMS = {
    "ai engineer",
    "analytics engineer",
    "applied scientist",
    "artificial intelligence",
    "backend developer",
    "backend engineer",
    "business intelligence analyst",
    "cloud architect",
    "cloud engineer",
    "data analyst",
    "data engineer",
    "data scientist",
    "devops engineer",
    "full stack developer",
    "full stack engineer",
    "infrastructure engineer",
    "machine learning",
    "ml engineer",
    "platform engineer",
    "product analyst",
    "site reliability engineer",
    "software developer",
    "software engineer",
}

EXCLUDED_TITLE_TERMS = {
    "account executive",
    "customer success",
    "data annotation",
    "director",
    "future opportunities",
    "legal",
    "manager",
    "marketing",
    "recruiter",
    "sales",
    "vice president",
}

TARGET_ROLE_CATEGORIES = {
    "AI/ML",
    "Analytics",
    "Cloud/AWS",
    "Data Engineering",
    "Data Science",
    "Software Engineering",
}


def is_target_technical_job(job: dict[str, object]) -> bool:
    """Return whether a title fits the technical roles analyzed by JobLens."""
    title = str(job.get("title", "")).strip().lower()

    if not title:
        return False

    if any(term in title for term in EXCLUDED_TITLE_TERMS):
        return False

    if title.startswith("vp ") or title.startswith("vp,"):
        return False

    return any(term in title for term in TARGET_TITLE_TERMS)


def parse_posting_date(value: object) -> datetime | None:
    """Parse common ISO date strings without requiring a source-specific format."""
    raw_value = str(value or "").strip()

    if not raw_value:
        return None

    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed_date = date.fromisoformat(raw_value[:10])
        except ValueError:
            return None
        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=UTC)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def is_posting_active(
    job: dict[str, object],
    *,
    as_of: datetime | None = None,
) -> bool:
    """Return False only when an explicit valid-through date has passed."""
    valid_through = parse_posting_date(job.get("valid_through"))

    if valid_through is None:
        return True

    current_time = as_of or datetime.now(UTC)
    return valid_through >= current_time


def normalize_canadian_job(
    job: dict[str, object],
) -> dict[str, object] | None:
    """Return a Canada-only job with consistent structured location fields."""
    normalized_location = normalize_canadian_location(
        job.get("location", ""),
        description=job.get("description", ""),
        address_locality=job.get("address_locality", ""),
        address_region=job.get("address_region", ""),
        address_country=job.get("address_country", ""),
        is_remote=(
            bool(job.get("is_remote", False))
            or "remote" in str(job.get("title", "")).lower()
        ),
        workplace_type=str(job.get("workplace_type", "")),
    )

    if normalized_location is None:
        return None

    return {
        **job,
        "original_location": str(job.get("location", "")).strip(),
        "location": normalized_location.normalized_location,
        "city": normalized_location.city,
        "province": normalized_location.province,
        "country": normalized_location.country,
        "workplace_type": normalized_location.workplace_type,
    }


def deduplicate_jobs(
    jobs: Iterable[dict[str, object]],
) -> list[dict[str, object]]:
    """Deduplicate jobs by stable ID, source URL, then visible identity."""
    deduplicated: list[dict[str, object]] = []
    seen_job_ids: set[str] = set()
    seen_source_urls: set[str] = set()
    seen_visible_keys: set[tuple[str, str, str]] = set()

    for job in jobs:
        job_id = str(job.get("job_id", "")).strip().lower()
        source_url = str(job.get("source_url", "")).strip().lower()
        visible_key = (
            str(job.get("company", "")).strip().lower(),
            str(job.get("title", "")).strip().lower(),
            str(job.get("location", "")).strip().lower(),
        )

        if (
            (job_id and job_id in seen_job_ids)
            or (source_url and source_url in seen_source_urls)
            or visible_key in seen_visible_keys
        ):
            continue

        if job_id:
            seen_job_ids.add(job_id)
        if source_url:
            seen_source_urls.add(source_url)
        seen_visible_keys.add(visible_key)
        deduplicated.append(job)

    return deduplicated


def prepare_canada_jobs(
    jobs: Iterable[dict[str, object]],
    *,
    as_of: datetime | None = None,
) -> list[dict[str, object]]:
    """Filter active technical postings to normalized Canadian jobs."""
    prepared_jobs: list[dict[str, object]] = []

    for job in jobs:
        if not is_target_technical_job(job):
            continue

        if not is_posting_active(job, as_of=as_of):
            continue

        normalized_job = normalize_canadian_job(job)

        if normalized_job is None:
            continue

        role_category = categorize_role(
            str(normalized_job.get("title", "")),
            str(normalized_job.get("description", "")),
        )

        if role_category not in TARGET_ROLE_CATEGORIES:
            continue

        normalized_job["role_category"] = role_category
        prepared_jobs.append(normalized_job)

    return deduplicate_jobs(prepared_jobs)


def posting_sort_key(job: dict[str, object]) -> tuple[str, str, str]:
    """Sort recent dated jobs first, then use stable visible fields."""
    parsed_date = parse_posting_date(job.get("date_posted"))
    sortable_date = (
        parsed_date.isoformat()
        if parsed_date is not None
        else ""
    )

    return (
        sortable_date,
        str(job.get("company", "")).lower(),
        str(job.get("title", "")).lower(),
    )


def select_balanced_jobs(
    jobs: Iterable[dict[str, object]],
    *,
    max_jobs: int = 72,
    max_per_company: int = 6,
    max_per_location: int = 18,
) -> list[dict[str, object]]:
    """Select a deterministic role-balanced snapshot with source diversity."""
    candidates = sorted(
        jobs,
        key=posting_sort_key,
        reverse=True,
    )
    category_queues = {
        category: [
            job for job in candidates
            if job.get("role_category") == category
        ]
        for category in sorted(TARGET_ROLE_CATEGORIES)
    }
    selected: list[dict[str, object]] = []
    company_counts: Counter[str] = Counter()
    location_counts: Counter[str] = Counter()

    while len(selected) < max_jobs and any(category_queues.values()):
        selected_this_round = False

        for category in sorted(category_queues):
            queue = category_queues[category]
            eligible_jobs = [
                (index, job)
                for index, job in enumerate(queue)
                if company_counts[str(job.get("company", "")).strip()]
                < max_per_company
                and location_counts[str(job.get("location", "")).strip()]
                < max_per_location
            ]

            if not eligible_jobs:
                queue.clear()
                continue

            selected_index, job = min(
                eligible_jobs,
                key=lambda item: (
                    location_counts[
                        str(item[1].get("location", "")).strip()
                    ],
                    company_counts[
                        str(item[1].get("company", "")).strip()
                    ],
                    item[0],
                ),
            )
            queue.pop(selected_index)

            company = str(job.get("company", "")).strip()
            location = str(job.get("location", "")).strip()
            selected.append(job)
            company_counts[company] += 1
            location_counts[location] += 1
            selected_this_round = True

            if len(selected) >= max_jobs:
                break

        if not selected_this_round:
            break

    return selected
