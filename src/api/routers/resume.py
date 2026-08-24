from fastapi import APIRouter

from src.analysis.job_services import get_available_skills
from src.api.schemas import ErrorResponse, ResumeSkillsRequest, ResumeSkillsResponse
from src.api.services.analysis_service import load_jobs_for_analysis
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

    Given a dataset, the skills its jobs ask for are searched for as well as
    the curated taxonomy, so the resume box and the skills list on the form
    recognise the same vocabulary instead of disagreeing.
    """
    dataset_skills: list[str] = []

    if request.dataset_name:
        _, jobs_df = load_jobs_for_analysis(request.dataset_name)
        dataset_skills = get_available_skills(jobs_df)

    return {
        "skills": extract_resume_skills(request.resume_text, dataset_skills),
    }
