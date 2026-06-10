import pytest
import requests

from src.ingestion.greenhouse_client import (
    GREENHOUSE_JOBS_URL,
    fetch_greenhouse_jobs,
    normalize_greenhouse_job,
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


def test_fetch_greenhouse_jobs_calls_expected_url_and_params(monkeypatch):
    calls = {}

    def fake_get(url, params, timeout):
        calls["url"] = url
        calls["params"] = params
        calls["timeout"] = timeout
        return FakeResponse({"jobs": [{"id": 123, "title": "Software Engineer"}]})

    monkeypatch.setattr(requests, "get", fake_get)

    jobs = fetch_greenhouse_jobs("ExampleCo", timeout_seconds=5)

    assert jobs == [{"id": 123, "title": "Software Engineer"}]
    assert calls["url"] == GREENHOUSE_JOBS_URL.format(company_slug="exampleco")
    assert calls["params"] == {"content": "true"}
    assert calls["timeout"] == 5


def test_fetch_greenhouse_jobs_rejects_empty_company_slug():
    with pytest.raises(ValueError, match="company_slug"):
        fetch_greenhouse_jobs("  ")


def test_fetch_greenhouse_jobs_rejects_missing_jobs_list(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({"not_jobs": []})

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(ValueError, match="jobs"):
        fetch_greenhouse_jobs("exampleco")


def test_fetch_greenhouse_jobs_raises_http_errors(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({}, status_error=requests.HTTPError("404"))

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        fetch_greenhouse_jobs("missingco")


def test_normalize_greenhouse_job_maps_to_raw_job_schema():
    job = {
        "id": 123,
        "title": "Senior Data Scientist",
        "absolute_url": "https://boards.greenhouse.io/example/jobs/123",
        "location": {"name": "Toronto, Canada"},
        "content": "<p>Build ML models with Python, SQL, and AWS.</p>",
        "departments": [{"name": "Data Science"}],
        "offices": [{"name": "Canada"}],
    }

    normalized = normalize_greenhouse_job(
        job,
        company_slug="example",
        fetched_at="2026-06-10T00:00:00+00:00",
    )

    assert normalized["job_id"] == "greenhouse:example:123"
    assert normalized["title"] == "Senior Data Scientist"
    assert normalized["company"] == "example"
    assert normalized["location"] == "Toronto, Canada"
    assert "Build ML models with Python, SQL, and AWS." in normalized["description"]
    assert "Data Science" in normalized["description"]
    assert normalized["experience_level"] == "Senior"
    assert normalized["source"] == "greenhouse"
    assert normalized["source_url"] == "https://boards.greenhouse.io/example/jobs/123"
    assert normalized["fetched_at"] == "2026-06-10T00:00:00+00:00"