from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from src.api.logging_config import (
    LOGGER_NAME,
    REQUEST_ID_HEADER,
    JsonLogFormatter,
    sanitize_request_id,
)
from src.api.main import app

client = TestClient(app)

RESUME_TEXT = (
    "Rishav Preet Singh, Toronto. Built pipelines with Python, SQL, and Airflow "
    "at ExampleCorp from 2023."
)


class RecordingHandler(logging.Handler):
    """Capture formatted output so the assertions see what would be shipped."""

    def __init__(self) -> None:
        super().__init__()
        self.setFormatter(JsonLogFormatter())
        self.lines: list[str] = []
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        self.lines.append(self.format(record))

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def payloads(self) -> list[dict]:
        return [json.loads(line) for line in self.lines]


@pytest.fixture
def captured_logs():
    handler = RecordingHandler()
    logger = logging.getLogger(LOGGER_NAME)
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    yield handler

    logger.removeHandler(handler)
    logger.setLevel(previous_level)


def test_json_formatter_emits_one_line_with_extra_fields() -> None:
    record = logging.LogRecord(
        name="joblens.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "abc123"
    record.status_code = 200

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "joblens.api"
    assert payload["message"] == "request completed"
    assert payload["request_id"] == "abc123"
    assert payload["status_code"] == 200
    assert payload["timestamp"].endswith("Z")


def test_sanitize_request_id_bounds_and_strips_unprintable_input() -> None:
    assert sanitize_request_id("  trace-1  ") == "trace-1"
    assert sanitize_request_id("bad\nid\r") == "badid"
    assert len(sanitize_request_id("x" * 200)) == 64


def test_request_gets_an_id_echoed_back(captured_logs) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER]

    payloads = [p for p in captured_logs.payloads() if p["message"] == "request completed"]

    assert len(payloads) == 1
    assert payloads[0]["method"] == "GET"
    assert payloads[0]["path"] == "/health"
    assert payloads[0]["status_code"] == 200
    assert isinstance(payloads[0]["duration_ms"], float)
    assert payloads[0]["request_id"] == response.headers[REQUEST_ID_HEADER]


def test_caller_supplied_request_id_is_reused_for_tracing(captured_logs) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: "frontend-42"})

    assert response.headers[REQUEST_ID_HEADER] == "frontend-42"
    assert '"request_id": "frontend-42"' in captured_logs.text


def test_logs_never_contain_resume_text(captured_logs) -> None:
    """The analyze endpoint receives resume text, so logging must stay metadata-only."""
    response = client.post(
        "/analyze",
        json={
            "current_skills": ["python"],
            "resume_text": RESUME_TEXT,
            "target_roles": [],
            "search_query": "",
            "search_mode": "tfidf",
            "location": "Any",
            "experience_level": "Any",
            "candidate_experience": "3-5 years",
            "top_n": 3,
        },
    )

    assert response.status_code in {200, 404}
    assert "Rishav" not in captured_logs.text
    assert "ExampleCorp" not in captured_logs.text
    assert RESUME_TEXT not in captured_logs.text


def test_logs_never_contain_query_strings(captured_logs) -> None:
    """Job search terms are user input and stay out of the log line."""
    client.get("/jobs", params={"search": "unlisted-employer-name", "limit": 1})

    assert "unlisted-employer-name" not in captured_logs.text
    assert any(p["path"] == "/jobs" for p in captured_logs.payloads())
