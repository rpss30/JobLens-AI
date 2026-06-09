"""Small Adzuna API client for fetching real job postings."""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv


ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class AdzunaClientError(RuntimeError):
    """Raised when the Adzuna API request fails."""


def get_adzuna_credentials() -> tuple[str, str, str]:
    """Load Adzuna API credentials from environment variables."""
    load_dotenv()

    app_id = os.getenv("ADZUNA_APP_ID", "").strip()
    app_key = os.getenv("ADZUNA_APP_KEY", "").strip()
    country = os.getenv("ADZUNA_COUNTRY", "ca").strip().lower() or "ca"

    if not app_id or not app_key:
        raise AdzunaClientError(
            "Missing ADZUNA_APP_ID or ADZUNA_APP_KEY. Add them to your local .env file."
        )

    return app_id, app_key, country


def fetch_adzuna_jobs(
    query: str,
    location: str,
    *,
    page: int = 1,
    results_per_page: int = 10,
    country: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch one page of jobs from the Adzuna search endpoint."""
    app_id, app_key, default_country = get_adzuna_credentials()
    selected_country = country or default_country

    url = f"{ADZUNA_BASE_URL}/{selected_country}/search/{page}"

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": query,
        "where": location,
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }

    response = requests.get(url, params=params, timeout=20)

    if response.status_code != 200:
        raise AdzunaClientError(
            f"Adzuna request failed with status {response.status_code}: {response.text[:300]}"
        )

    payload = response.json()
    results = payload.get("results", [])

    if not isinstance(results, list):
        raise AdzunaClientError("Unexpected Adzuna response format: results is not a list.")

    return results