from fastapi.testclient import TestClient
from src.api.main import app
from datetime import UTC, datetime
import pandas as pd

from src.api.services import analysis_run_service, analysis_service, dataset_service

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
            "candidate_experience": "3-5 years",
            "top_skills": 5,
            "top_jobs": 6,
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
    assert data["resume_analysis"] is None

    assert len(data["recommended_skills"]) <= 5
    assert len(data["top_matching_jobs"]) <= 6

    first_role_score = data["role_scores"][0]

    assert "role_category" in first_role_score
    assert "weighted_match_score" in first_role_score
    assert "matched_skills" in first_role_score
    assert "related_skills" in first_role_score
    assert "missing_skills" in first_role_score
    assert "representative_job_count" in first_role_score
    assert "sample_confidence" in first_role_score
    assert "headline_eligible" in first_role_score

    first_job_match = data["top_matching_jobs"][0]

    assert "related_skills_count" in first_job_match
    assert "related_skills_preview" in first_job_match
    assert "search_relevance" in first_job_match
    assert "source" in first_job_match
    assert "source_url" in first_job_match
    assert first_job_match["skill_match_score"] == first_job_match["job_match_score"]
    assert first_job_match["candidate_experience"] == "3-5 years"
    assert "required_experience" in first_job_match
    assert "required_experience_years" in first_job_match
    assert "experience_fit" in first_job_match
    assert "matched_required_skills" in first_job_match
    assert "missing_required_skills" in first_job_match
    assert "matched_preferred_skills" in first_job_match
    assert "missing_preferred_skills" in first_job_match
    assert "preferred_skill_coverage" in first_job_match


def test_analyze_accepts_legacy_top_n_for_result_limits() -> None:
    response = client.post(
        "/analyze",
        json={
            "current_skills": ["Python", "SQL", "Pandas"],
            "target_roles": ["Data Scientist"],
            "location": "Any",
            "experience_level": "Entry Level",
            "top_n": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["recommended_skills"]) <= 1
    assert len(data["top_matching_jobs"]) <= 1


def test_filter_options_expose_canada_snapshot_selections() -> None:
    response = client.get(
        "/filter-options",
        params={"dataset_name": "canada_snapshot"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["dataset_name"] == "canada_snapshot"
    assert data["target_roles"]
    assert data["role_categories"]
    assert data["skills"]
    assert data["locations"]

    # Derived from the dataset so filters always match stored values.
    assert "Senior" in data["experience_levels"]

    assert data["summary"]["job_count"] > 0
    assert data["summary"]["company_count"] > 0


def test_filter_options_return_404_for_unavailable_local_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service,
        "load_canada_snapshot_jobs",
        lambda: pd.DataFrame(),
    )
    monkeypatch.setitem(
        analysis_service.LOCAL_DATASET_LOADERS,
        analysis_service.CANADA_SNAPSHOT_DATASET_NAME,
        analysis_service.load_canada_snapshot_jobs,
    )

    response = client.get(
        "/filter-options",
        params={"dataset_name": "canada_snapshot"},
    )

    assert response.status_code == 404
    assert "canada_snapshot" in response.json()["detail"]


def test_candidate_report_downloads_markdown_and_pdf() -> None:
    request_body = {
        "current_skills": ["Python", "SQL", "Docker"],
        "search_query": "backend engineer",
        "dataset_name": "canada_snapshot",
        "top_n": 5,
    }

    markdown_response = client.post(
        "/reports/candidate",
        params={"format": "markdown"},
        json=request_body,
    )

    assert markdown_response.status_code == 200
    assert markdown_response.headers["content-type"].startswith("text/markdown")
    assert ".md" in markdown_response.headers["content-disposition"]
    assert "JobLens AI Candidate Skill-Gap Report" in markdown_response.text

    pdf_response = client.post(
        "/reports/candidate",
        params={"format": "pdf"},
        json=request_body,
    )

    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF-")

    unsupported_response = client.post(
        "/reports/candidate",
        params={"format": "docx"},
        json=request_body,
    )

    assert unsupported_response.status_code == 422


def test_jobs_support_search_sorting_and_pagination() -> None:
    response = client.get(
        "/jobs",
        params={"dataset_name": "canada_snapshot", "limit": 3},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["dataset_name"] == "canada_snapshot"
    assert data["total"] > 3
    assert len(data["jobs"]) == 3
    assert data["jobs"][0]["title"]
    assert data["jobs"][0]["source_url"]

    search_response = client.get(
        "/jobs",
        params={
            "dataset_name": "canada_snapshot",
            "search_query": "machine learning platform",
            "limit": 3,
        },
    )

    search_data = search_response.json()

    # A free-text query narrows the slice and ranks by relevance.
    assert search_data["total"] < data["total"]
    assert search_data["jobs"][0]["search_relevance"] > 0

    sorted_response = client.get(
        "/jobs",
        params={
            "dataset_name": "canada_snapshot",
            "sort_by": "company",
            "sort_order": "asc",
            "limit": 5,
        },
    )

    companies = [job["company"] for job in sorted_response.json()["jobs"]]

    assert companies == sorted(companies)

    assert client.get("/jobs", params={"sort_by": "unsupported"}).status_code == 422


def test_market_insights_summarize_demand_without_a_candidate_profile() -> None:
    response = client.post(
        "/market-insights",
        json={"dataset_name": "canada_snapshot", "top_n": 5},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["dataset_name"] == "canada_snapshot"
    assert data["jobs_analyzed"] > 0
    assert 0 < len(data["skill_demand"]) <= 5
    assert data["skill_demand"][0]["job_count"] > 0
    assert data["role_skill_importance"]
    assert data["jobs_by_location"]
    assert data["top_companies"]
    assert data["role_distribution"]

    no_match_response = client.post(
        "/market-insights",
        json={
            "dataset_name": "canada_snapshot",
            "search_query": "underwater basket weaving",
            "location": "Antarctica",
        },
    )

    assert no_match_response.status_code == 404


def test_analyze_supports_free_text_search_without_target_roles() -> None:
    response = client.post(
        "/analyze",
        json={
            "current_skills": ["Python", "SQL", "Pandas"],
            "target_roles": [],
            "search_query": "data scientist",
            "location": "Any",
            "experience_level": "Any",
            "top_skills": 5,
            "top_jobs": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["jobs_analyzed"] > 0
    assert data["top_matching_jobs"]
    assert data["top_matching_jobs"][0]["search_relevance"] > 0


def test_analyze_supports_semantic_search_mode() -> None:
    response = client.post(
        "/analyze",
        json={
            "current_skills": ["Python", "PostgreSQL", "Docker"],
            "target_roles": [],
            "search_query": "server-side database APIs",
            "search_mode": "semantic",
            "location": "Any",
            "experience_level": "Any",
            "top_skills": 5,
            "top_jobs": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()
    first_job_match = data["top_matching_jobs"][0]

    assert first_job_match["search_mode"] == "semantic"
    assert first_job_match["semantic_relevance"] > 0
    assert first_job_match["search_relevance"] == first_job_match[
        "semantic_relevance"
    ]


def test_analyze_supports_resume_text_without_manual_skills_or_search_scope() -> None:
    resume_text = """
    Built FastAPI REST APIs with Python, PostgreSQL, Docker, AWS, CI/CD,
    monitoring dashboards, and SQL-backed analytics projects.
    """

    response = client.post(
        "/analyze",
        json={
            "current_skills": [],
            "resume_text": resume_text,
            "target_roles": [],
            "search_query": "",
            "location": "Any",
            "experience_level": "Any",
            "top_skills": 5,
            "top_jobs": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()
    resume_analysis = data["resume_analysis"]
    serialized_response = str(data)

    assert resume_analysis["provided"] is True
    assert "not persisted" in resume_analysis["privacy_note"]
    assert resume_text.strip() not in serialized_response
    assert "python" in resume_analysis["combined_skills"]
    assert "postgresql" in resume_analysis["combined_skills"]
    assert resume_analysis["fit_score"] >= 0
    assert resume_analysis["learning_priorities"]
    assert resume_analysis["suggested_resume_keywords"]
    assert resume_analysis["top_matching_jobs"]
    assert resume_analysis["top_matching_jobs"][0]["explanation"]


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


def test_analyze_requires_a_search_query_or_target_role() -> None:
    response = client.post(
        "/analyze",
        json={
            "current_skills": ["Python"],
            "target_roles": [],
            "search_query": " ",
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

def make_zero_overlap_api_processed_jobs_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "job_id": None,
                "title": "Backend Software Engineer",
                "company": "TestCo",
                "location": "Remote",
                "description": "Build backend services using Go and Java.",
                "experience_level": "Senior",
                "clean_title": "backend software engineer",
                "clean_description": "build backend services using go and java",
                "extracted_skills": ["Go", "Java", "SQL"],
                "role_category": "Software Engineering",
                "skills_text": "Go, Java, SQL",
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
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        dataset_service.database_repository,
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


def test_list_datasets_supports_filter_sort_and_pagination(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        dataset_service.database_repository,
        "list_datasets",
        lambda: [
            {
                "name": "sample_jobs",
                "source_type": "sample_csv",
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
            },
            {
                "name": "zeta_upload",
                "source_type": "uploaded_csv",
                "created_at": datetime(2026, 1, 3, tzinfo=UTC),
            },
            {
                "name": "alpha_upload",
                "source_type": "uploaded_csv",
                "created_at": datetime(2026, 1, 2, tzinfo=UTC),
            },
        ],
    )

    response = client.get(
        "/datasets",
        params={
            "source_type": "uploaded_csv",
            "sort_by": "name",
            "sort_order": "asc",
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "zeta_upload"


def test_list_datasets_validates_query_parameters() -> None:
    response = client.get(
        "/datasets",
        params={
            "sort_by": "unsupported_field",
            "limit": 0,
        },
    )

    assert response.status_code == 422


def test_list_datasets_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: False,
    )

    response = client.get("/datasets")

    assert response.status_code == 503
    assert "PostgreSQL is unavailable" in response.json()["detail"]


def test_analyze_can_use_database_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        analysis_service.database_repository,
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
            "top_skills": 5,
            "top_jobs": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["dataset_name"] == "sample_jobs"
    assert data["jobs_analyzed"] == 1
    assert data["best_role"] == "Data Science"
    assert data["top_matching_jobs"][0]["title"] == "Data Scientist"


def test_analyze_omits_zero_score_top_matching_jobs(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        analysis_service.database_repository,
        "load_processed_jobs_dataframe",
        lambda dataset_name: make_zero_overlap_api_processed_jobs_df(),
    )

    response = client.post(
        "/analyze",
        json={
            "dataset_name": "sample_jobs",
            "current_skills": ["Python", "Docker"],
            "target_roles": ["Backend Software Engineer"],
            "location": "Any",
            "experience_level": "Any",
            "top_skills": 5,
            "top_jobs": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["best_role"] == "No skill overlap"
    assert data["weighted_match_score"] == 0.0
    assert data["top_matching_jobs"] == []


def test_analyze_database_dataset_returns_404_when_dataset_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        analysis_service.database_repository,
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

def test_create_analysis_run_saves_and_returns_the_run(monkeypatch) -> None:
    saved_calls = []

    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "save_analysis_run",
        lambda **kwargs: saved_calls.append(kwargs) or 1,
    )
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "load_analysis_run",
        lambda analysis_run_id: make_saved_analysis_run(),
    )

    response = client.post(
        "/analysis-runs",
        json={
            "dataset_name": "sample_jobs",
            "target_roles": ["Data Scientist"],
            "current_skills": ["Python", "SQL"],
            "best_role": "Data Science",
            "weighted_match_score": 75.5,
            "top_missing_skill": "spark",
            "jobs_analyzed": 20,
            "recommended_skills": ["spark"],
            "role_scores": [{"role_category": "Data Science"}],
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == 1

    # An omitted name falls back to a generated dated name.
    assert saved_calls[0]["name"].endswith("sample_jobs")


def test_create_analysis_run_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: False,
    )

    response = client.post(
        "/analysis-runs",
        json={"dataset_name": "sample_jobs"},
    )

    assert response.status_code == 503


def test_rename_and_delete_analysis_run(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "rename_analysis_run",
        lambda analysis_run_id, new_name: analysis_run_id == 1,
    )
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "delete_analysis_run",
        lambda analysis_run_id: analysis_run_id == 1,
    )

    rename_response = client.patch(
        "/analysis-runs/1",
        json={"new_name": "My saved check"},
    )

    assert rename_response.status_code == 200
    assert rename_response.json()["name"] == "My saved check"

    delete_response = client.delete("/analysis-runs/1")

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    # Unknown ids are reported rather than silently succeeding.
    assert (
        client.patch("/analysis-runs/404", json={"new_name": "x"}).status_code == 404
    )
    assert client.delete("/analysis-runs/404").status_code == 404


def test_list_analysis_runs_returns_saved_runs(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        analysis_run_service.database_repository,
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


def test_list_analysis_runs_supports_filter_sort_and_pagination(monkeypatch) -> None:
    first_run = make_saved_analysis_run()
    second_run = {
        **make_saved_analysis_run(),
        "id": 2,
        "name": "analysis_20260102_backend_sample_jobs",
        "jobs_analyzed": 5,
        "weighted_match_score": 40.0,
        "created_at": datetime(2026, 1, 2, tzinfo=UTC),
    }
    third_run = {
        **make_saved_analysis_run(),
        "id": 3,
        "name": "analysis_20260103_backend_other_dataset",
        "dataset_name": "other_dataset",
        "jobs_analyzed": 1,
        "weighted_match_score": 10.0,
        "created_at": datetime(2026, 1, 3, tzinfo=UTC),
    }

    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "list_analysis_runs",
        lambda: [first_run, second_run, third_run],
    )

    response = client.get(
        "/analysis-runs",
        params={
            "dataset_name": "sample_jobs",
            "sort_by": "jobs_analyzed",
            "sort_order": "asc",
            "limit": 1,
            "offset": 1,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["jobs_analyzed"] == 20


def test_list_analysis_runs_validates_query_parameters() -> None:
    response = client.get(
        "/analysis-runs",
        params={
            "sort_by": "unsupported_field",
            "offset": -1,
        },
    )

    assert response.status_code == 422


def test_list_analysis_runs_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: False,
    )

    response = client.get("/analysis-runs")

    assert response.status_code == 503
    assert "PostgreSQL is unavailable" in response.json()["detail"]


def test_get_analysis_run_returns_saved_run(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: True,
    )

    def fake_load_analysis_run(analysis_run_id: int) -> dict:
        assert analysis_run_id == 1
        return make_saved_analysis_run()

    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "load_analysis_run",
        fake_load_analysis_run,
    )

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
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "load_analysis_run",
        lambda analysis_run_id: None,
    )

    response = client.get("/analysis-runs/999")

    assert response.status_code == 404
    assert "Analysis run 999 was not found" in response.json()["detail"]


def test_get_analysis_run_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_run_service.database_repository,
        "check_database_connection",
        lambda: False,
    )

    response = client.get("/analysis-runs/1")

    assert response.status_code == 503
    assert "PostgreSQL is unavailable" in response.json()["detail"]

def test_upload_dataset_saves_processed_jobs(monkeypatch) -> None:
    saved_datasets = []

    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        dataset_service.database_repository,
        "save_uploaded_dataset_from_dataframe",
        lambda **kwargs: saved_datasets.append(kwargs) or "uploaded_sample",
    )

    with open("data/examples/sample_upload_jobs.csv", "rb") as upload_file:
        response = client.post(
            "/datasets",
            files={"file": ("sample_upload_jobs.csv", upload_file.read(), "text/csv")},
            data={"dataset_name": "uploaded sample"},
        )

    assert response.status_code == 201
    assert response.json()["dataset_name"] == "uploaded_sample"
    assert response.json()["job_count"] > 0

    # The CSV is processed before saving, so extracted skills are present.
    assert "extracted_skills" in saved_datasets[0]["df"].columns


def test_upload_dataset_rejects_invalid_uploads(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )

    non_csv_response = client.post(
        "/datasets",
        files={"file": ("jobs.txt", b"title,company\n", "text/plain")},
        data={"dataset_name": "invalid"},
    )

    assert non_csv_response.status_code == 400
    assert "CSV file" in non_csv_response.json()["detail"]

    missing_columns_response = client.post(
        "/datasets",
        files={"file": ("jobs.csv", b"title,company\nEngineer,Acme\n", "text/csv")},
        data={"dataset_name": "invalid"},
    )

    assert missing_columns_response.status_code == 400
    assert "missing required columns" in missing_columns_response.json()["detail"]


def test_delete_dataset_deletes_uploaded_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )

    def fake_delete_dataset(dataset_name: str) -> bool:
        assert dataset_name == "uploaded_20260101_sample_jobs"
        return True

    monkeypatch.setattr(
        dataset_service.database_repository,
        "delete_dataset",
        fake_delete_dataset,
    )

    response = client.delete("/datasets/uploaded_20260101_sample_jobs")

    assert response.status_code == 200

    data = response.json()

    assert data["dataset_name"] == "uploaded_20260101_sample_jobs"
    assert data["deleted"] is True


def test_delete_dataset_returns_404_when_dataset_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        dataset_service.database_repository,
        "delete_dataset",
        lambda dataset_name: False,
    )

    response = client.delete("/datasets/missing_dataset")

    assert response.status_code == 404
    assert "missing_dataset" in response.json()["detail"]


def test_delete_dataset_returns_400_for_protected_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )

    def fake_delete_dataset(dataset_name: str) -> bool:
        raise ValueError("Only uploaded CSV datasets can be deleted.")

    monkeypatch.setattr(
        dataset_service.database_repository,
        "delete_dataset",
        fake_delete_dataset,
    )

    response = client.delete("/datasets/sample_jobs")

    assert response.status_code == 400
    assert "Only uploaded CSV datasets can be deleted" in response.json()["detail"]


def test_delete_dataset_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: False,
    )

    response = client.delete("/datasets/uploaded_20260101_sample_jobs")

    assert response.status_code == 503
    assert "PostgreSQL is unavailable" in response.json()["detail"]


def test_rename_dataset_renames_uploaded_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )

    def fake_rename_dataset(dataset_name: str, new_name: str) -> bool:
        assert dataset_name == "uploaded_20260101_sample_jobs"
        assert new_name == "My Custom Dataset"
        return True

    monkeypatch.setattr(
        dataset_service.database_repository,
        "rename_dataset",
        fake_rename_dataset,
    )

    response = client.patch(
        "/datasets/uploaded_20260101_sample_jobs",
        json={"new_name": "My Custom Dataset"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["old_name"] == "uploaded_20260101_sample_jobs"
    assert data["new_name"] == "my_custom_dataset"
    assert data["renamed"] is True


def test_rename_dataset_returns_404_when_dataset_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )
    monkeypatch.setattr(
        dataset_service.database_repository,
        "rename_dataset",
        lambda dataset_name, new_name: False,
    )

    response = client.patch(
        "/datasets/missing_dataset",
        json={"new_name": "renamed_dataset"},
    )

    assert response.status_code == 404
    assert "missing_dataset" in response.json()["detail"]


def test_rename_dataset_returns_400_for_protected_dataset(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )

    def fake_rename_dataset(dataset_name: str, new_name: str) -> bool:
        raise ValueError("Only uploaded CSV datasets can be renamed.")

    monkeypatch.setattr(
        dataset_service.database_repository,
        "rename_dataset",
        fake_rename_dataset,
    )

    response = client.patch(
        "/datasets/sample_jobs",
        json={"new_name": "renamed_sample"},
    )

    assert response.status_code == 400
    assert "Only uploaded CSV datasets can be renamed" in response.json()["detail"]


def test_rename_dataset_returns_400_for_duplicate_target_name(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: True,
    )

    def fake_rename_dataset(dataset_name: str, new_name: str) -> bool:
        raise ValueError("Dataset name 'existing_dataset' already exists.")

    monkeypatch.setattr(
        dataset_service.database_repository,
        "rename_dataset",
        fake_rename_dataset,
    )

    response = client.patch(
        "/datasets/uploaded_20260101_sample_jobs",
        json={"new_name": "existing_dataset"},
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_rename_dataset_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        dataset_service.database_repository,
        "check_database_connection",
        lambda: False,
    )

    response = client.patch(
        "/datasets/uploaded_20260101_sample_jobs",
        json={"new_name": "renamed_dataset"},
    )

    assert response.status_code == 503
    assert "PostgreSQL is unavailable" in response.json()["detail"]
