import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.errors import ApiError, api_error_handler
from src.api.logging_config import configure_logging
from src.api.middleware import RequestContextMiddleware
from src.api.routers import (
    analysis_runs,
    analyze,
    datasets,
    filter_options,
    health,
    jobs,
    market_insights,
    reports,
)
from src.api.security import get_cors_origins


def get_api_root_path() -> str:
    return os.getenv("JOBLENS_API_ROOT_PATH", "").strip().rstrip("/")


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="JobLens AI API",
        description="Backend API for JobLens AI role-fit and skill-gap analysis.",
        version="0.4.0",
        root_path=get_api_root_path(),
        openapi_tags=[
            {
                "name": "health",
                "description": "Operational health checks.",
            },
            {
                "name": "datasets",
                "description": "PostgreSQL dataset selection and management.",
            },
            {
                "name": "analysis-runs",
                "description": "Saved role-fit analysis history.",
            },
            {
                "name": "filter-options",
                "description": "Selectable analysis filters for a dataset.",
            },
            {
                "name": "jobs",
                "description": "Job posting browse and search.",
            },
            {
                "name": "market-insights",
                "description": "Market-level skill, location, and employer demand.",
            },
            {
                "name": "analysis",
                "description": "Candidate role-fit and skill-gap analysis.",
            },
            {
                "name": "reports",
                "description": "Downloadable candidate skill-gap reports.",
            },
        ],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    # Starlette applies the last registered middleware outermost, so this sits
    # outside CORS: every request gets an ID and a log line, including the
    # preflights and rejections CORS answers by itself.
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(ApiError, api_error_handler)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        logging.getLogger("joblens.api").exception(
            "Unhandled API error on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error."},
        )

    app.include_router(health.router)
    app.include_router(datasets.router)
    app.include_router(analysis_runs.router)
    app.include_router(filter_options.router)
    app.include_router(jobs.router)
    app.include_router(market_insights.router)
    app.include_router(reports.router)
    app.include_router(analyze.router)

    return app
