"""Security-oriented API helpers for local and deployed FastAPI surfaces."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from fastapi import Request

from src.api.errors import ApiError


logger = logging.getLogger("joblens.api")

DEFAULT_CORS_ORIGINS = (
    "http://localhost:8501",
    "http://localhost:8502",
    "http://127.0.0.1:8501",
    "http://127.0.0.1:8502",
)


@dataclass(frozen=True)
class RateLimitConfig:
    max_requests: int = 60
    window_seconds: int = 60
    enabled: bool = True


def parse_csv_env(value: str | None) -> list[str]:
    return [
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    ]


def get_cors_origins() -> list[str]:
    configured_origins = parse_csv_env(os.getenv("JOBLENS_CORS_ORIGINS"))
    return configured_origins or list(DEFAULT_CORS_ORIGINS)


def get_rate_limit_config() -> RateLimitConfig:
    enabled = os.getenv("JOBLENS_RATE_LIMIT_ENABLED", "true").strip().lower()

    return RateLimitConfig(
        max_requests=max(1, int(os.getenv("JOBLENS_ANALYZE_RATE_LIMIT", "60"))),
        window_seconds=max(1, int(os.getenv("JOBLENS_RATE_LIMIT_WINDOW_SECONDS", "60"))),
        enabled=enabled not in {"0", "false", "no", "off"},
    )


class InMemoryRateLimiter:
    """Small per-process rate limiter for expensive unauthenticated endpoints."""

    def __init__(self) -> None:
        self._requests_by_client: dict[str, Deque[float]] = defaultdict(deque)

    def clear(self) -> None:
        self._requests_by_client.clear()

    def check(
        self,
        *,
        client_id: str,
        config: RateLimitConfig,
        now: float | None = None,
    ) -> None:
        if not config.enabled:
            return

        request_time = now if now is not None else time.monotonic()
        window_start = request_time - config.window_seconds
        request_times = self._requests_by_client[client_id]

        while request_times and request_times[0] <= window_start:
            request_times.popleft()

        if len(request_times) >= config.max_requests:
            raise ApiError(
                status_code=429,
                detail="Rate limit exceeded. Please wait before running another analysis.",
            )

        request_times.append(request_time)


analyze_rate_limiter = InMemoryRateLimiter()


def get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown-client"


def rate_limit_analyze(request: Request) -> None:
    analyze_rate_limiter.check(
        client_id=get_client_identifier(request),
        config=get_rate_limit_config(),
    )
