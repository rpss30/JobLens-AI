# src/database/repository.py

import ast
from typing import Any

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.database.db import get_db_session
from src.database.models import Dataset, JobPosting, JobSkill, ProcessedJob, Skill


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