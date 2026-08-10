from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from src.matching.experience import (
    EXPERIENCE_BUCKETS,
    NO_CANDIDATE_EXPERIENCE,
    normalize_candidate_experience_bucket,
)


MAX_SKILL_COUNT = 50
MAX_TARGET_ROLE_COUNT = 20
MAX_LIST_ITEM_LENGTH = 80


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: str


class AnalyzeRequest(BaseModel):
    current_skills: list[str] = Field(
        default_factory=list,
        max_length=MAX_SKILL_COUNT,
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
        max_length=MAX_TARGET_ROLE_COUNT,
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
        max_length=120,
        description="Location filter. Use 'Any' to disable location filtering.",
    )
    experience_level: str = Field(
        default="Any",
        max_length=80,
        description="Experience level filter. Use 'Any' to disable filtering.",
    )
    candidate_experience: str = Field(
        default=NO_CANDIDATE_EXPERIENCE,
        max_length=40,
        description=(
            "Candidate's relevant professional experience bucket. Used as a "
            "soft fit signal separate from the experience level filter."
        ),
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Number of recommended skills and matching jobs to return.",
    )
    dataset_name: str | None = Field(
        default=None,
        max_length=120,
        description=(
            "Optional PostgreSQL dataset name. If omitted, the API uses "
            "the local sample dataset."
        ),
    )

    @field_validator("current_skills", "target_roles")
    @classmethod
    def clean_text_list(cls, values: list[str]) -> list[str]:
        cleaned_values = []

        for value in values:
            cleaned_value = str(value).strip()

            if not cleaned_value:
                continue

            if len(cleaned_value) > MAX_LIST_ITEM_LENGTH:
                raise ValueError(
                    f"List values must be {MAX_LIST_ITEM_LENGTH} characters or fewer."
                )

            cleaned_values.append(cleaned_value)

        return cleaned_values

    @field_validator("candidate_experience")
    @classmethod
    def clean_candidate_experience(cls, value: str) -> str:
        cleaned_value = str(value or "").strip()

        if not cleaned_value:
            return NO_CANDIDATE_EXPERIENCE

        if cleaned_value not in EXPERIENCE_BUCKETS:
            return normalize_candidate_experience_bucket(cleaned_value)

        return cleaned_value

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


class DatasetSnapshotSummary(BaseModel):
    job_count: int
    company_count: int
    location_count: int
    refreshed_date: str


class FilterOptionsResponse(BaseModel):
    dataset_name: str
    target_roles: list[str]
    role_categories: list[str]
    skills: list[str]
    locations: list[str]
    experience_levels: list[str]
    summary: DatasetSnapshotSummary


class UploadDatasetResponse(BaseModel):
    dataset_name: str
    job_count: int


class DeleteDatasetResponse(BaseModel):
    dataset_name: str
    deleted: bool

class RenameDatasetRequest(BaseModel):
    new_name: str = Field(..., min_length=1)


class RenameDatasetResponse(BaseModel):
    old_name: str
    new_name: str
    renamed: bool


class CreateAnalysisRunRequest(BaseModel):
    name: str = Field(
        default="",
        max_length=255,
        description=(
            "Optional readable name. A dated name is generated when omitted."
        ),
    )
    dataset_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Dataset the analysis was run against.",
    )
    target_roles: list[str] = Field(
        default_factory=list,
        max_length=MAX_TARGET_ROLE_COUNT,
    )
    location: str = Field(default="Any", max_length=120)
    experience_level: str = Field(default="Any", max_length=80)
    current_skills: list[str] = Field(
        default_factory=list,
        max_length=MAX_SKILL_COUNT,
    )
    best_role: str | None = Field(default=None, max_length=120)
    weighted_match_score: float | None = Field(default=None, ge=0, le=100)
    top_missing_skill: str | None = Field(default=None, max_length=MAX_LIST_ITEM_LENGTH)
    jobs_analyzed: int = Field(default=0, ge=0)
    recommended_skills: list[str] = Field(
        default_factory=list,
        max_length=MAX_SKILL_COUNT,
    )
    role_scores: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=MAX_TARGET_ROLE_COUNT,
        description="Saved role score rows from the analysis response.",
    )

    @field_validator("current_skills", "target_roles", "recommended_skills")
    @classmethod
    def clean_text_list(cls, values: list[str]) -> list[str]:
        cleaned_values = []

        for value in values:
            cleaned_value = str(value).strip()

            if not cleaned_value:
                continue

            if len(cleaned_value) > MAX_LIST_ITEM_LENGTH:
                raise ValueError(
                    f"List values must be {MAX_LIST_ITEM_LENGTH} characters or fewer."
                )

            cleaned_values.append(cleaned_value)

        return cleaned_values


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
    
class JobListing(BaseModel):
    job_id: str = ""
    title: str
    company: str
    location: str
    experience_level: str
    role_category: str
    employment_type: str = ""
    workplace_type: str = ""
    is_remote: bool = False
    date_posted: str = ""
    source: str = ""
    source_url: str = ""
    skills: list[str] = Field(default_factory=list)
    search_relevance: float = 0.0


class JobListResponse(BaseModel):
    dataset_name: str
    total: int
    limit: int
    offset: int
    jobs: list[JobListing]


class MarketInsightsRequest(BaseModel):
    target_roles: list[str] = Field(
        default_factory=list,
        max_length=MAX_TARGET_ROLE_COUNT,
        description="Target job titles or role keywords.",
    )
    search_query: str = Field(
        default="",
        max_length=200,
        description="Optional free-text query used to narrow the market slice.",
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
        max_length=120,
        description="Location filter. Use 'Any' to disable location filtering.",
    )
    experience_level: str = Field(
        default="Any",
        max_length=80,
        description="Experience level filter. Use 'Any' to disable filtering.",
    )
    top_n: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Number of ranked rows to return per insight.",
    )
    dataset_name: str | None = Field(
        default=None,
        max_length=120,
        description=(
            "Optional dataset name. If omitted, the API uses the local "
            "sample dataset."
        ),
    )

    @field_validator("target_roles")
    @classmethod
    def clean_target_roles(cls, values: list[str]) -> list[str]:
        cleaned_values = []

        for value in values:
            cleaned_value = str(value).strip()

            if not cleaned_value:
                continue

            if len(cleaned_value) > MAX_LIST_ITEM_LENGTH:
                raise ValueError(
                    f"List values must be {MAX_LIST_ITEM_LENGTH} characters or fewer."
                )

            cleaned_values.append(cleaned_value)

        return cleaned_values


class SkillDemand(BaseModel):
    skill: str
    job_count: int


class RoleSkillImportance(BaseModel):
    role_category: str
    skill: str
    job_count: int
    role_weight: int
    weighted_importance: float


class LocationDemand(BaseModel):
    location: str
    job_count: int


class CompanyDemand(BaseModel):
    company: str
    job_count: int


class RoleDistribution(BaseModel):
    role_category: str
    job_count: int


class MarketInsightsResponse(BaseModel):
    dataset_name: str
    jobs_analyzed: int
    skill_demand: list[SkillDemand]
    role_skill_importance: list[RoleSkillImportance]
    jobs_by_location: list[LocationDemand]
    top_companies: list[CompanyDemand]
    role_distribution: list[RoleDistribution]


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
    source: str = ""
    source_url: str = ""
    search_relevance: float
    semantic_relevance: float = 0.0
    tfidf_relevance: float = 0.0
    search_mode: str = "tfidf"
    job_match_score: float
    skill_match_score: float
    candidate_experience: str
    required_experience: str
    required_experience_years: int | None = None
    experience_requirement_source: str
    experience_fit: str
    experience_fit_score: float | None = None
    matched_skills_count: int
    related_skills_count: int
    missing_skills_count: int
    matched_skills_preview: str
    related_skills_preview: str
    missing_skills_preview: str
    matched_required_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    preferred_skill_coverage: float | None = None


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
