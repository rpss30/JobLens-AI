# tests/conftest.py

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def sample_processed_jobs_df() -> pd.DataFrame:
    rows = [
        {
            "job_id": "job-backend-1",
            "title": "Backend Software Engineer",
            "clean_title": "backend software engineer",
            "company": "APIWorks",
            "location": "Toronto, ON",
            "city": "Toronto",
            "province": "ON",
            "experience_level": "Entry Level",
            "role_category": "Software Engineering",
            "description": "Build REST APIs with Python, PostgreSQL, Docker, and AWS.",
            "clean_description": "build rest apis with python postgresql docker and aws",
            "extracted_skills": ["Python", "REST APIs", "PostgreSQL", "Docker", "AWS"],
            "skills_text": "Python REST APIs PostgreSQL Docker AWS",
            "source": "greenhouse",
            "source_url": "https://example.com/jobs/backend-1",
            "fetched_at": "2026-07-01T12:00:00+00:00",
        },
        {
            "job_id": "job-ml-1",
            "title": "Machine Learning Engineer",
            "clean_title": "machine learning engineer",
            "company": "ModelLab",
            "location": "Vancouver, BC",
            "city": "Vancouver",
            "province": "BC",
            "experience_level": "Entry Level",
            "role_category": "AI/ML",
            "description": "Train PyTorch models and deploy MLflow pipelines.",
            "clean_description": "train pytorch models and deploy mlflow pipelines",
            "extracted_skills": ["Python", "PyTorch", "MLflow", "model deployment"],
            "skills_text": "Python PyTorch MLflow model deployment",
            "source": "lever",
            "source_url": "https://example.com/jobs/ml-1",
            "fetched_at": "2026-07-01T12:00:00+00:00",
        },
        {
            "job_id": "job-analytics-1",
            "title": "Analytics Engineer",
            "clean_title": "analytics engineer",
            "company": "MetricWorks",
            "location": "Calgary, AB",
            "city": "Calgary",
            "province": "AB",
            "experience_level": "Mid Level",
            "role_category": "Analytics",
            "description": "Build dashboards with SQL, dbt, Tableau, and product metrics.",
            "clean_description": "build dashboards with sql dbt tableau and product metrics",
            "extracted_skills": ["SQL", "dbt", "Tableau", "product metrics"],
            "skills_text": "SQL dbt Tableau product metrics",
            "source": "ashby",
            "source_url": "https://example.com/jobs/analytics-1",
            "fetched_at": "2026-07-01T12:00:00+00:00",
        },
    ]

    return pd.DataFrame(rows)


@pytest.fixture
def backend_resume_text() -> str:
    return (
        "Built FastAPI REST APIs with Python, PostgreSQL, Docker, AWS, "
        "CI/CD workflows, monitoring dashboards, and SQL analytics."
    )


@pytest.fixture
def resume_analyze_payload(backend_resume_text: str) -> dict:
    return {
        "current_skills": [],
        "resume_text": backend_resume_text,
        "target_roles": [],
        "search_query": "",
        "location": "Any",
        "experience_level": "Any",
        "top_n": 5,
    }


@pytest.fixture
def saved_analysis_run_payload() -> dict:
    return {
        "id": 1,
        "name": "analysis_20260701_backend_sample_jobs",
        "dataset_name": "sample_jobs",
        "target_roles": ["Backend Engineer"],
        "location": "Any",
        "experience_level": "Entry Level",
        "current_skills": ["Python", "PostgreSQL", "Docker"],
        "best_role": "Software Engineering",
        "weighted_match_score": 82.5,
        "top_missing_skill": "aws",
        "jobs_analyzed": 12,
        "recommended_skills": ["aws", "terraform"],
        "role_scores": [
            {
                "role_category": "Software Engineering",
                "weighted_match_score": 82.5,
            }
        ],
    }
