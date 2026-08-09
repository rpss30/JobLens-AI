from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from src.api.schemas import AnalyzeRequest, ErrorResponse
from src.api.security import rate_limit_analyze
from src.api.services import report_service
from src.api.services.report_service import ReportFormat


router = APIRouter(tags=["reports"])


@router.post(
    "/reports/candidate",
    summary="Download a candidate skill-gap report",
    dependencies=[Depends(rate_limit_analyze)],
    response_class=Response,
    responses={
        200: {
            "content": {
                "text/markdown": {},
                "application/pdf": {},
            },
            "description": "Generated candidate skill-gap report.",
        },
        404: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def download_candidate_report(
    request: AnalyzeRequest,
    report_format: Annotated[
        ReportFormat,
        Query(
            alias="format",
            description="Report format to generate.",
        ),
    ] = "markdown",
) -> Response:
    content, media_type, filename = report_service.generate_candidate_report(
        request,
        report_format,
    )

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
