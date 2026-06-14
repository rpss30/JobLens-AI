from fastapi.testclient import TestClient
from src.api.main import app
from datetime import UTC, datetime
import pandas as pd

from src.api import main as api_main

client = TestClient(app)

def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_candidate_fit_summary() -> None:
    response = client.post(
        "/analyze",
        json={
            "current_skills": ["Python", "SQL", "Pandas"],
            "target_roles": ["Data Scientist"],
            "location": "Any",
            "experience_level": "Entry Level",
            "top_n": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["dataset_name"] == "local_sample"
    assert data["jobs_analyzed"] > 0
    assert data["best_role"]
    assert data["weighted_match_score"] >= 0
    assert data["top_missing_skill"]

    assert "recommended_skills" in data
    assert "role_scores" in data
    assert "top_matching_jobs" in data

    assert len(data["recommended_skills"]) <= 5
    assert len(data["top_matching_jobs"]) <= 5

    first_role_score = data["role_scores"][0]

    assert "role_category" in first_role_score
    assert "weighted_match_score" in first_role_score
    assert "matched_skills" in first_role_score
    assert "missing_skills" in first_role_score


def test_analyze_returns_404_when_no_jobs_match() -> None:
    response = client.post(
        "/analyze",
        json={
            "current_skills": ["Python"],
            "target_roles": ["Quantum Banana Engineer"],
            "location": "Nowhere",
            "experience_level": "Senior Level",
        },
    )

    assert response.status_code == 404
    assert "No matching jobs found" in response.json()["detail"]


def test_analyze_validates_required_skills_and_roles() -> None:
    response = client.post(
        "/analyze",
        json={
            "current_skills": [],
            "target_roles": [],
            "location": "Any",
            "experience_level": "Any",
        },
    )

    assert response.status_code == 422

def make_api_processed_jobs_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "job_id": None,
                "title": "Data Scientist",
                "company": "TestCo",
                "location": "Toronto ON",
                "description": "Analyze data using Python, SQL, Pandas, and statistics.",
                "experience_level": "Entry Level",
                "clean_title": "data scientist",
                "clean_description": "analyze data using python sql pandas and statistics",
                "extracted_skills": ["Python", "SQL", "Pandas", "statistics"],
                "role_category": "Data Science",
                "skills_text": "Python, SQL, Pandas, statistics",
            }
        ]
    )

def make_saved_analysis_run() -> dict:
    return {
        "id": 1,
        "name": "analysis_20260101_data_science_sample_jobs",
        "dataset_name": "sample_jobs",
        "target_roles": ["Data Scientist"],
        "location": "Any",
        "experience_level": "Entry Level",
        "current_skills": ["Python", "SQL", "Pandas"],
        "best_role": "Data Science",
        "weighted_match_score": 75.5,
        "top_missing_skill": "spark",
        "jobs_analyzed": 20,
        "recommended_skills": ["spark", "statistics"],
        "role_scores": [
            {
                "role_category": "Data Science",
                "weighted_match_score": 75.5,
            }
        ],
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }

def test_list_datasets_returns_database_datasets(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: True)
    monkeypatch.setattr(
        api_main,
        "list_datasets",
        lambda: [
            {
                "name": "sample_jobs",
                "source_type": "sample_csv",
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            }
        ],
    )

    response = client.get("/datasets")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "sample_jobs"
    assert data[0]["source_type"] == "sample_csv"
    assert "created_at" in data[0]


def test_list_datasets_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: False)

    response = client.get("/datasets")

    assert response.status_code == 503
    assert "PostgreSQL is unavailable" in response.json()["detail"]


def test_analyze_can_use_database_dataset(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: True)
    monkeypatch.setattr(
        api_main,
        "load_processed_jobs_dataframe",
        lambda dataset_name: make_api_processed_jobs_df(),
    )

    response = client.post(
        "/analyze",
        json={
            "dataset_name": "sample_jobs",
            "current_skills": ["Python", "SQL", "Pandas"],
            "target_roles": ["Data Scientist"],
            "location": "Any",
            "experience_level": "Entry Level",
            "top_n": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["dataset_name"] == "sample_jobs"
    assert data["jobs_analyzed"] == 1
    assert data["best_role"] == "Data Science"
    assert data["top_matching_jobs"][0]["title"] == "Data Scientist"


def test_analyze_database_dataset_returns_404_when_dataset_missing(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: True)
    monkeypatch.setattr(
        api_main,
        "load_processed_jobs_dataframe",
        lambda dataset_name: pd.DataFrame(),
    )

    response = client.post(
        "/analyze",
        json={
            "dataset_name": "missing_dataset",
            "current_skills": ["Python"],
            "target_roles": ["Data Scientist"],
            "location": "Any",
            "experience_level": "Any",
        },
    )

    assert response.status_code == 404
    assert "missing_dataset" in response.json()["detail"]

def test_list_analysis_runs_returns_saved_runs(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: True)
    monkeypatch.setattr(
        api_main,
        "list_analysis_runs",
        lambda: [make_saved_analysis_run()],
    )

    response = client.get("/analysis-runs")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["name"] == "analysis_20260101_data_science_sample_jobs"
    assert data[0]["dataset_name"] == "sample_jobs"
    assert data[0]["target_roles"] == ["Data Scientist"]
    assert data[0]["current_skills"] == ["Python", "SQL", "Pandas"]
    assert data[0]["best_role"] == "Data Science"
    assert data[0]["weighted_match_score"] == 75.5
    assert data[0]["top_missing_skill"] == "spark"
    assert data[0]["jobs_analyzed"] == 20
    assert data[0]["recommended_skills"] == ["spark", "statistics"]
    assert "role_scores" in data[0]
    assert "created_at" in data[0]


def test_list_analysis_runs_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: False)

    response = client.get("/analysis-runs")

    assert response.status_code == 503
    assert "PostgreSQL is unavailable" in response.json()["detail"]


def test_get_analysis_run_returns_saved_run(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: True)

    def fake_load_analysis_run(analysis_run_id: int) -> dict:
        assert analysis_run_id == 1
        return make_saved_analysis_run()

    monkeypatch.setattr(api_main, "load_analysis_run", fake_load_analysis_run)

    response = client.get("/analysis-runs/1")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["dataset_name"] == "sample_jobs"
    assert data["target_roles"] == ["Data Scientist"]
    assert data["current_skills"] == ["Python", "SQL", "Pandas"]
    assert data["best_role"] == "Data Science"
    assert data["recommended_skills"] == ["spark", "statistics"]


def test_get_analysis_run_returns_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: True)
    monkeypatch.setattr(api_main, "load_analysis_run", lambda analysis_run_id: None)

    response = client.get("/analysis-runs/999")

    assert response.status_code == 404
    assert "Analysis run 999 was not found" in response.json()["detail"]


def test_get_analysis_run_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "check_database_connection", lambda: False)

    response = client.get("/analysis-runs/1")

    assert response.status_code == 503
    assert "PostgreSQL is unavailable" in response.json()["detail"]