from io import BytesIO

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.services import analysis_service
from src.dashboard.services import read_uploaded_jobs_csv, validate_uploaded_jobs_csv
from src.ingestion.pipeline_runs import validate_job_records
from src.resume.resume_analyzer import PRIVACY_NOTE, analyze_resume_against_jobs


client = TestClient(app)


def test_api_rejects_invalid_search_mode(resume_analyze_payload: dict) -> None:
    payload = {
        **resume_analyze_payload,
        "search_mode": "vector",
    }

    response = client.post("/analyze", json=payload)

    assert response.status_code == 422


def test_api_rejects_oversized_resume_text(resume_analyze_payload: dict) -> None:
    payload = {
        **resume_analyze_payload,
        "resume_text": "Python " + ("x" * 12_001),
    }

    response = client.post("/analyze", json=payload)

    assert response.status_code == 422


def test_api_resume_analysis_does_not_echo_raw_resume_text(
    monkeypatch,
    sample_processed_jobs_df: pd.DataFrame,
    resume_analyze_payload: dict,
) -> None:
    monkeypatch.setattr(
        analysis_service,
        "load_jobs_for_analysis",
        lambda dataset_name: ("fixture_jobs", sample_processed_jobs_df),
    )

    response = client.post("/analyze", json=resume_analyze_payload)

    assert response.status_code == 200

    data = response.json()
    serialized_response = str(data)

    assert data["dataset_name"] == "fixture_jobs"
    assert data["resume_analysis"]["privacy_note"] == PRIVACY_NOTE
    assert resume_analyze_payload["resume_text"] not in serialized_response


def test_uploaded_csv_reader_rejects_malformed_rows() -> None:
    malformed_csv = BytesIO(
        b'title,company,location,description,experience_level\n'
        b'Backend Engineer,APIWorks,Toronto,"Build APIs,Entry Level\n'
    )

    with pytest.raises(pd.errors.ParserError):
        read_uploaded_jobs_csv(malformed_csv)


def test_uploaded_csv_validation_reports_blank_required_fields() -> None:
    uploaded_df = pd.DataFrame(
        [
            {
                "title": " ",
                "company": "APIWorks",
                "location": "Toronto, ON",
                "description": "Build APIs.",
                "experience_level": "Entry Level",
            }
        ]
    )

    is_valid, message = validate_uploaded_jobs_csv(uploaded_df)

    assert is_valid is False
    assert "blank values" in message
    assert "title" in message


def test_ingestion_validation_reports_empty_records() -> None:
    assert validate_job_records([]) == ["No normalized jobs were produced."]


def test_ingestion_validation_reports_duplicate_source_urls(
    sample_processed_jobs_df: pd.DataFrame,
) -> None:
    job_records = sample_processed_jobs_df.to_dict(orient="records")
    job_records[1]["source_url"] = job_records[0]["source_url"]

    errors = validate_job_records(job_records)

    assert (
        "Duplicate source_url values found: https://example.com/jobs/backend-1."
        in errors
    )


def test_resume_analysis_handles_empty_job_set_without_private_text(
    sample_processed_jobs_df: pd.DataFrame,
    backend_resume_text: str,
) -> None:
    analysis = analyze_resume_against_jobs(
        jobs_df=sample_processed_jobs_df.head(0),
        resume_text=backend_resume_text,
    )

    assert analysis["provided"] is True
    assert analysis["privacy_note"] == PRIVACY_NOTE
    assert analysis["top_matching_jobs"] == []
    assert analysis["fit_score"] == 0.0
    assert backend_resume_text not in str(analysis)
