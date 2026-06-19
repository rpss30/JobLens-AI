import pytest
import requests

from src.ingestion.ashby_client import (
    ASHBY_POSTINGS_URL,
    fetch_ashby_postings,
    normalize_ashby_posting,
)


class FakeResponse:
    def __init__(self, payload, status_error: Exception | None = None):
        self._payload = payload
        self._status_error = status_error

    def raise_for_status(self):
        if self._status_error:
            raise self._status_error

    def json(self):
        return self._payload


def test_fetch_ashby_postings_calls_expected_url_and_params(monkeypatch):
    calls = {}

    def fake_get(url, params, timeout):
        calls["url"] = url
        calls["params"] = params
        calls["timeout"] = timeout
        return FakeResponse({"jobs": [{"title": "Data Engineer"}]})

    monkeypatch.setattr(requests, "get", fake_get)

    postings = fetch_ashby_postings("Example", timeout_seconds=5)

    assert postings == [{"title": "Data Engineer"}]
    assert calls["url"] == ASHBY_POSTINGS_URL.format(job_board_name="Example")
    assert calls["params"] == {"includeCompensation": "true"}
    assert calls["timeout"] == 5


def test_fetch_ashby_postings_rejects_empty_board_name():
    with pytest.raises(ValueError, match="job_board_name"):
        fetch_ashby_postings(" ")


def test_fetch_ashby_postings_requires_jobs_list(monkeypatch):
    monkeypatch.setattr(
        requests,
        "get",
        lambda url, params, timeout: FakeResponse({"not_jobs": []}),
    )

    with pytest.raises(ValueError, match="jobs"):
        fetch_ashby_postings("Example")


def test_normalize_ashby_posting_maps_extended_schema():
    posting = {
        "id": "job-123",
        "title": "Senior Data Engineer",
        "location": "Toronto, Ontario, Canada",
        "descriptionPlain": "Build pipelines with Python, SQL, and AWS.",
        "publishedAt": "2026-06-10T00:00:00+00:00",
        "employmentType": "FullTime",
        "workplaceType": "Hybrid",
        "isRemote": False,
        "jobUrl": "https://jobs.ashbyhq.com/example/job-123",
        "address": {
            "postalAddress": {
                "addressLocality": "Toronto",
                "addressRegion": "Ontario",
                "addressCountry": "Canada",
            }
        },
    }

    normalized = normalize_ashby_posting(
        posting,
        company_name="Example Company",
        job_board_name="Example",
        fetched_at="2026-06-18T00:00:00+00:00",
    )

    assert normalized["job_id"] == "ashby:example:job-123"
    assert normalized["company"] == "Example Company"
    assert normalized["location"] == "Toronto, Ontario, Canada"
    assert normalized["address_locality"] == "Toronto"
    assert normalized["address_region"] == "Ontario"
    assert normalized["address_country"] == "Canada"
    assert normalized["date_posted"] == "2026-06-10T00:00:00+00:00"
    assert normalized["source"] == "ashby"
