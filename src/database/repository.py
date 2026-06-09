# src/database/repository.py

import ast
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.database.db import get_db_session
from src.database.models import AnalysisRun, Dataset, JobPosting, JobSkill, ProcessedJob, Skill


RAW_COLUMNS = [
    "title",
    "company",
    "location",
    "description",
    "experience_level",
]

PROCESSED_COLUMNS = [
    "clean_title",
    "clean_description",
    "extracted_skills",
    "role_category",
    "skills_text",
]


def normalize_skill_name(skill: str) -> str:
    return skill.strip().lower()


def parse_skills(value: Any) -> list[str]:
    """
    Convert extracted_skills into a clean Python list.

    Handles:
    - already-existing lists
    - stringified lists from CSV
    - comma-separated strings
    - empty values
    """
    if isinstance(value, list):
        return [str(skill).strip() for skill in value if str(skill).strip()]

    if pd.isna(value):
        return []

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        try:
            parsed = ast.literal_eval(value)

            if isinstance(parsed, list):
                return [str(skill).strip() for skill in parsed if str(skill).strip()]
        except (ValueError, SyntaxError):
            pass

        return [skill.strip() for skill in value.split(",") if skill.strip()]

    return []

def slugify_dataset_name(value: str) -> str:
    """
    Convert a filename or dataset label into a safe dataset name.
    """
    cleaned_value = value.strip().lower()
    cleaned_value = re.sub(r"[^a-z0-9]+", "_", cleaned_value)
    cleaned_value = cleaned_value.strip("_")

    return cleaned_value or "uploaded_dataset"


def build_uploaded_dataset_name(filename: str) -> str:
    """
    Build a unique dataset name for an uploaded CSV file.
    """
    file_stem = Path(filename).stem
    safe_file_stem = slugify_dataset_name(file_stem)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    return f"uploaded_{timestamp}_{safe_file_stem}"

def build_analysis_run_name(best_role: str | None, dataset_name: str) -> str:
    """
    Build a readable default name for a saved analysis run.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_dataset_name = slugify_dataset_name(dataset_name)

    if best_role:
        safe_role_name = slugify_dataset_name(best_role)
        return f"analysis_{timestamp}_{safe_role_name}_{safe_dataset_name}"

    return f"analysis_{timestamp}_{safe_dataset_name}"

def check_database_connection() -> bool:
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_or_create_dataset(
    session: Session,
    name: str,
    source_type: str = "sample_csv",
) -> Dataset:
    stmt = select(Dataset).where(Dataset.name == name)
    dataset = session.execute(stmt).scalar_one_or_none()

    if dataset:
        return dataset

    dataset = Dataset(name=name, source_type=source_type)
    session.add(dataset)
    session.flush()

    return dataset


def get_or_create_skill(session: Session, skill_name: str) -> Skill:
    normalized_name = normalize_skill_name(skill_name)

    stmt = select(Skill).where(Skill.normalized_name == normalized_name)
    skill = session.execute(stmt).scalar_one_or_none()

    if skill:
        return skill

    skill = Skill(name=skill_name.strip(), normalized_name=normalized_name)
    session.add(skill)
    session.flush()

    return skill


def clear_dataset(session: Session, dataset_name: str) -> None:
    stmt = select(Dataset).where(Dataset.name == dataset_name)
    dataset = session.execute(stmt).scalar_one_or_none()

    if dataset:
        session.delete(dataset)
        session.flush()


def seed_processed_jobs_from_dataframe(
    df: pd.DataFrame,
    dataset_name: str = "sample_jobs",
    source_type: str = "sample_csv",
    replace_existing: bool = True,
) -> int:
    """
    Load processed jobs from a dataframe into PostgreSQL.
    """
    required_columns = set(RAW_COLUMNS + PROCESSED_COLUMNS)
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns for database seed: {sorted(missing_columns)}"
        )

    with get_db_session() as session:
        if replace_existing:
            clear_dataset(session, dataset_name)

        dataset = get_or_create_dataset(
            session=session,
            name=dataset_name,
            source_type=source_type,
        )

        inserted_count = 0

        for _, row in df.iterrows():
            job_posting = JobPosting(
                dataset_id=dataset.id,
                job_id=str(row.get("job_id", "")) if "job_id" in df.columns else None,
                title=str(row["title"]),
                company=str(row["company"]),
                location=str(row["location"]),
                description=str(row["description"]),
                experience_level=str(row["experience_level"]),
            )

            session.add(job_posting)
            session.flush()

            skills = list(dict.fromkeys(parse_skills(row["extracted_skills"])))

            processed_job = ProcessedJob(
                job_posting_id=job_posting.id,
                clean_title=str(row["clean_title"]),
                clean_description=str(row["clean_description"]),
                role_category=str(row["role_category"]),
                extracted_skills=skills,
                skills_text=str(row["skills_text"]),
            )

            session.add(processed_job)
            session.flush()

            for skill_name in skills:
                skill = get_or_create_skill(session, skill_name)

                job_skill = JobSkill(
                    processed_job_id=processed_job.id,
                    skill_id=skill.id,
                )

                session.add(job_skill)

            inserted_count += 1

        return inserted_count

def list_datasets() -> list[dict[str, Any]]:
    """
    List datasets stored in PostgreSQL.
    """
    with get_db_session() as session:
        stmt = select(
            Dataset.name,
            Dataset.source_type,
            Dataset.created_at,
        ).order_by(Dataset.created_at.desc())

        rows = session.execute(stmt).all()

    return [
        {
            "name": row.name,
            "source_type": row.source_type,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def save_uploaded_dataset_from_dataframe(
    df: pd.DataFrame,
    filename: str,
) -> str:
    """
    Save a processed uploaded jobs dataframe as a new PostgreSQL dataset.
    """
    dataset_name = build_uploaded_dataset_name(filename)

    seed_processed_jobs_from_dataframe(
        df=df,
        dataset_name=dataset_name,
        source_type="uploaded_csv",
        replace_existing=False,
    )

    return dataset_name

def load_processed_jobs_dataframe(dataset_name: str = "sample_jobs") -> pd.DataFrame:
    """
    Load processed jobs from PostgreSQL into the same dataframe shape
    expected by the Streamlit dashboard.
    """
    with get_db_session() as session:
        stmt = (
            select(
                JobPosting.job_id,
                JobPosting.title,
                JobPosting.company,
                JobPosting.location,
                JobPosting.description,
                JobPosting.experience_level,
                ProcessedJob.clean_title,
                ProcessedJob.clean_description,
                ProcessedJob.extracted_skills,
                ProcessedJob.role_category,
                ProcessedJob.skills_text,
            )
            .join(ProcessedJob, ProcessedJob.job_posting_id == JobPosting.id)
            .join(Dataset, Dataset.id == JobPosting.dataset_id)
            .where(Dataset.name == dataset_name)
            .order_by(JobPosting.id)
        )

        rows = session.execute(stmt).all()

    return pd.DataFrame(
        rows,
        columns=[
            "job_id",
            "title",
            "company",
            "location",
            "description",
            "experience_level",
            "clean_title",
            "clean_description",
            "extracted_skills",
            "role_category",
            "skills_text",
        ],
    )

def save_analysis_run(
    *,
    name: str,
    dataset_name: str,
    target_roles: list[str],
    location: str,
    experience_level: str,
    current_skills: list[str],
    best_role: str | None,
    weighted_match_score: float | None,
    top_missing_skill: str | None,
    jobs_analyzed: int,
    recommended_skills: list[str],
    role_scores: list[dict[str, Any]],
) -> int:
    """
    Save a completed dashboard analysis run to PostgreSQL.
    """
    with get_db_session() as session:
        stmt = select(Dataset).where(Dataset.name == dataset_name)
        dataset = session.execute(stmt).scalar_one_or_none()

        analysis_run = AnalysisRun(
            dataset_id=dataset.id if dataset else None,
            name=name,
            dataset_name=dataset_name,
            target_roles=target_roles,
            location=location,
            experience_level=experience_level,
            current_skills=current_skills,
            best_role=best_role,
            weighted_match_score=weighted_match_score,
            top_missing_skill=top_missing_skill,
            jobs_analyzed=jobs_analyzed,
            recommended_skills=recommended_skills,
            role_scores=role_scores,
        )

        session.add(analysis_run)
        session.flush()

        return analysis_run.id


def list_analysis_runs() -> list[dict[str, Any]]:
    """
    List saved analysis runs from newest to oldest.
    """
    with get_db_session() as session:
        stmt = select(
            AnalysisRun.id,
            AnalysisRun.name,
            AnalysisRun.dataset_name,
            AnalysisRun.best_role,
            AnalysisRun.weighted_match_score,
            AnalysisRun.jobs_analyzed,
            AnalysisRun.created_at,
        ).order_by(AnalysisRun.created_at.desc())

        rows = session.execute(stmt).all()

    return [
        {
            "id": row.id,
            "name": row.name,
            "dataset_name": row.dataset_name,
            "best_role": row.best_role,
            "weighted_match_score": row.weighted_match_score,
            "jobs_analyzed": row.jobs_analyzed,
            "created_at": row.created_at,
        }
        for row in rows
    ]


def load_analysis_run(analysis_run_id: int) -> dict[str, Any] | None:
    """
    Load a single saved analysis run by ID.
    """
    with get_db_session() as session:
        analysis_run = session.get(AnalysisRun, analysis_run_id)

        if analysis_run is None:
            return None

        return {
            "id": analysis_run.id,
            "name": analysis_run.name,
            "dataset_name": analysis_run.dataset_name,
            "target_roles": analysis_run.target_roles,
            "location": analysis_run.location,
            "experience_level": analysis_run.experience_level,
            "current_skills": analysis_run.current_skills,
            "best_role": analysis_run.best_role,
            "weighted_match_score": analysis_run.weighted_match_score,
            "top_missing_skill": analysis_run.top_missing_skill,
            "jobs_analyzed": analysis_run.jobs_analyzed,
            "recommended_skills": analysis_run.recommended_skills,
            "role_scores": analysis_run.role_scores,
            "created_at": analysis_run.created_at,
        }