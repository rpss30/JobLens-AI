"""Per-request correlation and access logging."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.logging_config import (
    LOGGER_NAME,
    REQUEST_ID_HEADER,
    request_id_var,
    sanitize_request_id,
)

logger = logging.getLogger(f"{LOGGER_NAME}.api")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Tag each request with an ID and log its outcome.

    The ID is taken from the incoming header when present, so a request can be
    followed from the reverse proxy through the Next.js server into the API, and
    generated otherwise. It is echoed back so a caller can quote it in a report.

    Only the method, route path, status, and duration are logged. Query strings
    are excluded because job search terms are user input.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_id = sanitize_request_id(request.headers.get(REQUEST_ID_HEADER, ""))
        request_id = incoming_id or uuid4().hex
        token = request_id_var.set(request_id)
        started_at = time.perf_counter()

        def elapsed_ms() -> float:
            return round((time.perf_counter() - started_at) * 1000, 2)

        try:
            response = await call_next(request)
        except Exception:
            # The app's exception handler turns this into a 500 response; this
            # records that the request itself ended in failure.
            logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": elapsed_ms(),
                },
            )
            raise
        finally:
            request_id_var.reset(token)

        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": elapsed_ms(),
            },
        )
        response.headers[REQUEST_ID_HEADER] = request_id

        return response
