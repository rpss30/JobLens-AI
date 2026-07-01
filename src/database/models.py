# src/database/models.py

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="sample_csv")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    job_postings: Mapped[list["JobPosting"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    ingestion_runs: Mapped[list["IngestionRun"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_datasets_source_type_created_at", "source_type", "created_at"),
    )


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)

    job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    experience_level: Mapped[str] = mapped_column(String(100), nullable=False)

    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    date_posted: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    valid_through: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    workplace_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    address_locality: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_updated_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    dataset: Mapped["Dataset"] = relationship(back_populates="job_postings")
    processed_job: Mapped[Optional["ProcessedJob"]] = relationship(
        back_populates="job_posting",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint("dataset_id", "job_id", name="uq_job_posting_dataset_job_id"),
        UniqueConstraint(
            "dataset_id",
            "source_url",
            name="uq_job_posting_dataset_source_url",
        ),
        Index("ix_job_postings_dataset_company", "dataset_id", "company"),
        Index("ix_job_postings_dataset_location", "dataset_id", "location"),
        Index(
            "ix_job_postings_dataset_experience_level",
            "dataset_id",
            "experience_level",
        ),
        Index("ix_job_postings_dataset_source", "dataset_id", "source"),
        Index("ix_job_postings_dataset_fetched_at", "dataset_id", "fetched_at"),
    )


class ProcessedJob(Base):
    __tablename__ = "processed_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id"),
        nullable=False,
        unique=True,
    )

    clean_title: Mapped[str] = mapped_column(String(255), nullable=False)
    clean_description: Mapped[str] = mapped_column(Text, nullable=False)
    role_category: Mapped[str] = mapped_column(String(100), nullable=False)

    extracted_skills: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    skills_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    skill_extraction_provider: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    skill_extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    job_posting: Mapped["JobPosting"] = relationship(back_populates="processed_job")
    job_skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="processed_job",
        cascade="all, delete-orphan",
    )

    extraction_results: Mapped[list["ExtractionResult"]] = relationship(
        back_populates="processed_job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_processed_jobs_role_category", "role_category"),
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)


class JobSkill(Base):
    __tablename__ = "job_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    processed_job_id: Mapped[int] = mapped_column(ForeignKey("processed_jobs.id"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False)

    processed_job: Mapped["ProcessedJob"] = relationship(back_populates="job_skills")
    skill: Mapped["Skill"] = relationship()

    __table_args__ = (
        UniqueConstraint("processed_job_id", "skill_id", name="uq_job_skill"),
    )

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("datasets.id"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(255), nullable=False)

    target_roles: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="Any")
    experience_level: Mapped[str] = mapped_column(String(100), nullable=False, default="Any")
    current_skills: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    best_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weighted_match_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    top_missing_skill: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    jobs_analyzed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    recommended_skills: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    role_scores: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
    )

    dataset: Mapped[Optional["Dataset"]] = relationship(back_populates="analysis_runs")

    __table_args__ = (
        Index("ix_analysis_runs_dataset_created_at", "dataset_id", "created_at"),
        Index("ix_analysis_runs_dataset_name_created_at", "dataset_name", "created_at"),
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("datasets.id"), nullable=True)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    total_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_sources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_job_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_log: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    dataset: Mapped[Optional["Dataset"]] = relationship(back_populates="ingestion_runs")

    __table_args__ = (
        Index("ix_ingestion_runs_status_started_at", "status", "started_at"),
        Index("ix_ingestion_runs_dataset_started_at", "dataset_id", "started_at"),
    )


class ExtractionResult(Base):
    __tablename__ = "extraction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    processed_job_id: Mapped[int] = mapped_column(ForeignKey("processed_jobs.id"), nullable=False)

    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extracted_skills: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    processed_job: Mapped["ProcessedJob"] = relationship(back_populates="extraction_results")

    __table_args__ = (
        Index("ix_extraction_results_processed_job_created_at", "processed_job_id", "created_at"),
        Index("ix_extraction_results_provider_created_at", "provider", "created_at"),
    )
