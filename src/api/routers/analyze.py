from fastapi import APIRouter, Depends

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from src.api.security import rate_limit_analyze
from src.api.services import analysis_service


router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze candidate role fit",
    dependencies=[Depends(rate_limit_analyze)],
    responses={
        429: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def analyze_jobs(request: AnalyzeRequest) -> AnalyzeResponse:
    return analysis_service.analyze_jobs(request)
