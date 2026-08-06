from fastapi import APIRouter

from src.api.schemas import HealthResponse


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API availability",
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}
