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
    matched_weight: int
    total_possible_weight: int
    matched_skills: list[str]
    missing_skills: list[str]


class JobMatch(BaseModel):
    title: str
    company: str
    location: str
    experience_level: str
    role_category: str
    job_match_score: float
    matched_skills_count: int
    missing_skills_count: int
    matched_skills_preview: str
    missing_skills_preview: str


class AnalyzeResponse(BaseModel):
    best_role: str
    weighted_match_score: float
    top_missing_skill: str
    jobs_analyzed: int
    recommended_skills: list[RecommendedSkill]
    role_scores: list[RoleScore]
    top_matching_jobs: list[JobMatch]