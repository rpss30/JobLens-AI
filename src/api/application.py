from fastapi import FastAPI

from src.api.errors import ApiError, api_error_handler
from src.api.routers import analysis_runs, analyze, datasets, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="JobLens AI API",
        description="Backend API for JobLens AI role-fit and skill-gap analysis.",
        version="0.4.0",
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
                "name": "analysis",
                "description": "Candidate role-fit and skill-gap analysis.",
            },
        ],
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(health.router)
    app.include_router(datasets.router)
    app.include_router(analysis_runs.router)
    app.include_router(analyze.router)

    return app
