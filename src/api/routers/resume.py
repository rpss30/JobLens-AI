from fastapi import APIRouter

from src.api.schemas import ErrorResponse, ResumeSkillsRequest, ResumeSkillsResponse
from src.resume.resume_analyzer import extract_resume_skills


router = APIRouter(tags=["resume"])


@router.post(
    "/resume/skills",
    response_model=ResumeSkillsResponse,
    summary="Extract known skills from pasted resume text",
    responses={500: {"model": ErrorResponse}},
)
def get_resume_skills(request: ResumeSkillsRequest) -> dict:
    """
    Pull skills out of a resume without running a full analysis.

    The analyze endpoint already does this as a side effect, but only once the
    whole request is submitted. Exposing it on its own lets a client show the
    skills it found while the person is still filling the form, and keeps the
    extraction itself in one place rather than reimplementing it client-side.
    """
    return {"skills": extract_resume_skills(request.resume_text)}
