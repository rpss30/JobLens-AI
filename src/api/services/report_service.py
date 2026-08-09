from typing import Literal

from src.api.schemas import AnalyzeRequest
from src.api.services.analysis_service import compute_analysis_frames
from src.dashboard.services import (
    generate_candidate_report_markdown,
    generate_candidate_report_pdf,
    get_candidate_fit_summary,
    get_job_match_details,
)


ReportFormat = Literal["markdown", "pdf"]

REPORT_FILENAMES: dict[str, str] = {
    "markdown": "joblens_candidate_skill_gap_report.md",
    "pdf": "joblens_candidate_skill_gap_report.pdf",
}

REPORT_MEDIA_TYPES: dict[str, str] = {
    "markdown": "text/markdown; charset=utf-8",
    "pdf": "application/pdf",
}


def generate_candidate_report(
    request: AnalyzeRequest,
    report_format: ReportFormat,
) -> tuple[bytes, str, str]:
    """Render a candidate skill-gap report and its download metadata."""
    frames = compute_analysis_frames(request)

    job_match_details_df = get_job_match_details(
        filtered_jobs=frames.filtered_jobs,
        user_skills=frames.analysis_skills,
    )
    candidate_fit_summary = get_candidate_fit_summary(
        filtered_jobs=frames.filtered_jobs,
        role_scores_df=frames.role_scores_df,
        recommended_skills_df=frames.recommended_skills_df,
    )

    report_arguments = {
        "current_skills": frames.analysis_skills,
        "target_roles": request.target_roles,
        "location": request.location,
        "experience_level": request.experience_level,
        "filtered_jobs": frames.filtered_jobs,
        "role_scores_df": frames.role_scores_df,
        "recommended_skills_df": frames.recommended_skills_df,
        "job_match_details_df": job_match_details_df,
        "candidate_fit_summary": candidate_fit_summary,
        "dataset_name": frames.dataset_name,
        "search_query": request.search_query,
        "search_mode": request.search_mode,
    }

    if report_format == "pdf":
        content = generate_candidate_report_pdf(**report_arguments)
    else:
        content = generate_candidate_report_markdown(**report_arguments).encode(
            "utf-8"
        )

    return (
        content,
        REPORT_MEDIA_TYPES[report_format],
        REPORT_FILENAMES[report_format],
    )
