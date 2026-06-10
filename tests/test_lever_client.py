import pytest
import requests

from src.ingestion.lever_client import (
    LEVER_POSTINGS_URL,
    fetch_lever_postings,
    normalize_lever_posting
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


def test_fetch_lever_postings_calls_expected_url_and_params(monkeypatch):
    calls = {}

    def fake_get(url, params, timeout):
        calls["url"] = url
        calls["params"] = params
        calls["timeout"] = timeout
        return FakeResponse([{"id": "job-1", "text": "Software Engineer"}])

    monkeypatch.setattr(requests, "get", fake_get)

    postings = fetch_lever_postings("ExampleCo", timeout_seconds=5)

    assert postings == [{"id": "job-1", "text": "Software Engineer"}]
    assert calls["url"] == LEVER_POSTINGS_URL.format(company_slug="exampleco")
    assert calls["params"] == {"mode": "json"}
    assert calls["timeout"] == 5


def test_fetch_lever_postings_rejects_empty_company_slug():
    with pytest.raises(ValueError, match="company_slug"):
        fetch_lever_postings("  ")


def test_fetch_lever_postings_rejects_non_list_payload(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse({"id": "not-a-list"})

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(ValueError, match="list"):
        fetch_lever_postings("exampleco")


def test_fetch_lever_postings_raises_http_errors(monkeypatch):
    def fake_get(url, params, timeout):
        return FakeResponse([], status_error=requests.HTTPError("404"))

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        fetch_lever_postings("missingco")

def test_normalize_lever_posting_maps_to_raw_job_schema():
    posting = {
        "id": "abc123",
        "text": "Senior Machine Learning Engineer",
        "hostedUrl": "https://jobs.lever.co/example/abc123",
        "categories": {
            "team": "Engineering",
            "location": "Toronto, Canada",
        },
        "description": "<p>Build ML systems with Python and PyTorch.</p>",
        "lists": [
            {
                "text": "Requirements",
                "content": [
                    "<li>Experience with AWS</li>",
                    "<li>Experience with Docker</li>",
                ],
            }
        ],
    }

    normalized = normalize_lever_posting(
        posting,
        company_slug="example",
        fetched_at="2026-06-10T00:00:00+00:00",
    )

    assert normalized["job_id"] == "lever:example:abc123"
    assert normalized["title"] == "Senior Machine Learning Engineer"
    assert normalized["company"] == "Engineering"
    assert normalized["location"] == "Toronto, Canada"
    assert "Build ML systems with Python and PyTorch." in normalized["description"]
    assert "Experience with AWS" in normalized["description"]
    assert "Experience with Docker" in normalized["description"]
    assert normalized["experience_level"] == "Senior"
    assert normalized["source"] == "lever"
    assert normalized["source_url"] == "https://jobs.lever.co/example/abc123"
    assert normalized["fetched_at"] == "2026-06-10T00:00:00+00:00"