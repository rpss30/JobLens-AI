from fastapi import APIRouter

from src.api.schemas import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from src.api.services import analysis_service


router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze candidate role fit",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def analyze_jobs(request: AnalyzeRequest) -> AnalyzeResponse:
    return analysis_service.analyze_jobs(request)
