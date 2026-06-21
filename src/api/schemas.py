from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    current_skills: list[str] = Field(
        ...,
        min_length=1,
        description="Candidate's current skills.",
    )
    target_roles: list[str] = Field(
        ...,
        min_length=1,
        description="Target job titles or role keywords.",
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
    job_match_score: float
    matched_skills_count: int
    related_skills_count: int
    missing_skills_count: int
    matched_skills_preview: str
    related_skills_preview: str
    missing_skills_preview: str


class AnalyzeResponse(BaseModel):
    dataset_name: str
    best_role: str
    weighted_match_score: float
    top_missing_skill: str
    jobs_analyzed: int
    recommended_skills: list[RecommendedSkill]
    role_scores: list[RoleScore]
    top_matching_jobs: list[JobMatch]
