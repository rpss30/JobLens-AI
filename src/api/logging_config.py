"""Structured application logging for the API.

Ingestion runs already record their own telemetry, but nothing described what the
API itself was doing in production. This emits one JSON line per request, plus
JSON for any application log record, so container logs can be filtered and
correlated by request instead of read by eye.

Request bodies, query strings, and headers are deliberately never logged: the
analyze and report endpoints receive resume text.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

LOGGER_NAME = "joblens"
REQUEST_ID_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 64

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Anything not set by the logging module itself arrived through `extra=` and
# belongs in the emitted payload.
_RESERVED_RECORD_KEYS = frozenset(
    vars(logging.makeLogRecord({})).keys()
) | frozenset({"message", "asctime", "taskName"})


def sanitize_request_id(value: str) -> str:
    """Keep a caller-supplied request ID printable and bounded.

    JSON encoding already neutralizes newline injection, but an unbounded or
    control-character-laden ID would still make logs unpleasant to read.
    """
    printable = "".join(
        character for character in value.strip() if character.isprintable()
    )

    return printable[:MAX_REQUEST_ID_LENGTH]


class JsonLogFormatter(logging.Formatter):
    """Render log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", "") or request_id_var.get()

        if request_id:
            payload["request_id"] = request_id

        for key, value in vars(record).items():
            if key not in _RESERVED_RECORD_KEYS and key != "request_id":
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def get_log_level() -> int:
    configured = os.getenv("JOBLENS_LOG_LEVEL", "INFO").strip().upper()

    return getattr(logging, configured, logging.INFO)


def use_json_logs() -> bool:
    return os.getenv("JOBLENS_LOG_FORMAT", "json").strip().lower() != "text"


def configure_logging() -> logging.Logger:
    """Attach a single stdout handler to the application logger.

    Idempotent, because the app factory runs on every import in tests and the
    module is imported once per Gunicorn worker. Propagation is left on so
    pytest's caplog and any host logging configuration still see the records.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(get_log_level())

    for existing in logger.handlers:
        if getattr(existing, "_joblens_handler", False):
            return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonLogFormatter() if use_json_logs() else logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
        ),
    )
    handler._joblens_handler = True  # type: ignore[attr-defined]
    logger.addHandler(handler)

    return logger
