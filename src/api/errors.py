from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass
class ApiError(Exception):
    """Application-level API error with a stable HTTP response shape."""

    status_code: int
    detail: str


async def api_error_handler(
    request: Request,
    error: ApiError,
) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": error.detail},
    )
