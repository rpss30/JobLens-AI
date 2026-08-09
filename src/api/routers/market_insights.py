from fastapi import APIRouter

from src.api.schemas import (
    ErrorResponse,
    MarketInsightsRequest,
    MarketInsightsResponse,
)
from src.api.services import market_insights_service


router = APIRouter(tags=["market-insights"])


@router.post(
    "/market-insights",
    response_model=MarketInsightsResponse,
    summary="Summarize skill, location, and employer demand",
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_market_insights(request: MarketInsightsRequest) -> MarketInsightsResponse:
    return market_insights_service.get_market_insights(request)
