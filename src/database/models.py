# src/database/models.py

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    dataset: Mapped["Dataset"] = relationship(back_populates="job_postings")
    processed_job: Mapped[Optional["ProcessedJob"]] = relationship(
        back_populates="job_posting",
        cascade="all, delete-orphan",
        uselist=False,
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

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    job_posting: Mapped["JobPosting"] = relationship(back_populates="processed_job")
    job_skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="processed_job",
        cascade="all, delete-orphan",
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