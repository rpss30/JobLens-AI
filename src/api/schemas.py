from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ErrorResponse(BaseModel):
    detail: str


class AnalyzeRequest(BaseModel):
    current_skills: list[str] = Field(
        default_factory=list,
        description="Candidate's current skills.",
    )
    resume_text: str = Field(
        default="",
        max_length=12_000,
        description=(
            "Optional pasted resume text for in-memory analysis. Raw text is "
            "not persisted or returned."
        ),
    )
    target_roles: list[str] = Field(
        default_factory=list,
        description="Target job titles or role keywords.",
    )
    search_query: str = Field(
        default="",
        max_length=200,
        description="Optional free-text query used to rank relevant jobs.",
    )
    search_mode: Literal["tfidf", "semantic", "hybrid"] = Field(
        default="tfidf",
        description=(
            "Search ranking mode. Use 'tfidf' for lexical relevance, "
            "'semantic' for dense local similarity, or 'hybrid' to blend both."
        ),
    )
    location: str = Field(
        default="Any",
        description="Location filter. Use 'Any' to disable location filtering.",
    )
    experience_level: str = Field(
        default="Any",
        description="Experience level filter. Use 'Any' to disable filtering.",
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Number of recommended skills and matching jobs to return.",
    )
    dataset_name: str | None = Field(
        default=None,
        description=(
            "Optional PostgreSQL dataset name. If omitted, the API uses "
            "the local sample dataset."
        ),
    )

    @model_validator(mode="after")
    def require_search_scope(self) -> "AnalyzeRequest":
        has_candidate_profile = bool(self.resume_text.strip()) or any(
            skill.strip() for skill in self.current_skills
        )

        if not has_candidate_profile:
            raise ValueError(
                "Provide at least one current skill or pasted resume text."
            )

        if (
            not self.resume_text.strip()
            and not self.search_query.strip()
            and not any(role.strip() for role in self.target_roles)
        ):
            raise ValueError(
                "Provide a search query, at least one target role, or pasted resume text."
            )

        return self


class DatasetSummary(BaseModel):
    name: str
    source_type: str
    created_at: datetime

class DeleteDatasetResponse(BaseModel):
    dataset_name: str
    deleted: bool

class RenameDatasetRequest(BaseModel):
    new_name: str = Field(..., min_length=1)


class RenameDatasetResponse(BaseModel):
    old_name: str
    new_name: str
    renamed: bool


class AnalysisRunResponse(BaseModel):
    id: int
    name: str
    dataset_name: str
    target_roles: list[str]
    location: str
    experience_level: str
    current_skills: list[str]
    best_role: str | None
    weighted_match_score: float | None
    top_missing_skill: str | None
    jobs_analyzed: int
    recommended_skills: list[str]
    role_scores: list[dict[str, Any]]
    created_at: datetime
    
class RecommendedSkill(BaseModel):
    skill: str
    score: float
    job_count: int
    avg_weight: float


class RoleScore(BaseModel):
    role_category: str
    sample_size: int
    weighted_match_score: float
    unweighted_match_score: float
    matched_weight: float
    total_possible_weight: float
    matched_skills: list[str]
    related_skills: list[str]
    missing_skills: list[str]
    representative_job_count: int
    sample_confidence: str
    headline_eligible: bool


class JobMatch(BaseModel):
    title: str
    company: str
    location: str
    experience_level: str
    role_category: str
    search_relevance: float
    semantic_relevance: float = 0.0
    tfidf_relevance: float = 0.0
    search_mode: str = "tfidf"
    job_match_score: float
    matched_skills_count: int
    related_skills_count: int
    missing_skills_count: int
    matched_skills_preview: str
    related_skills_preview: str
    missing_skills_preview: str


class LearningPriority(BaseModel):
    skill: str
    priority_score: float
    job_count: int
    reason: str


class ResumeJobMatch(BaseModel):
    title: str
    company: str
    location: str
    role_category: str
    fit_score: float
    skill_fit_score: float
    resume_similarity: float
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: str


class ResumeAnalysis(BaseModel):
    provided: bool
    privacy_note: str
    resume_skills: list[str]
    combined_skills: list[str]
    experience_areas: list[str]
    project_keywords: list[str]
    fit_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    learning_priorities: list[LearningPriority]
    suggested_resume_keywords: list[str]
    top_matching_jobs: list[ResumeJobMatch]
    explanation: str


class AnalyzeResponse(BaseModel):
    dataset_name: str
    best_role: str
    weighted_match_score: float
    top_missing_skill: str
    jobs_analyzed: int
    recommended_skills: list[RecommendedSkill]
    role_scores: list[RoleScore]
    top_matching_jobs: list[JobMatch]
    resume_analysis: ResumeAnalysis | None = None
