from datetime import UTC, datetime

import pytest

from ops import services as ops_services
from ops.app import create_app


@pytest.fixture()
def client():
    app = create_app({"TESTING": True})
    return app.test_client()


def patch_empty_loaders(monkeypatch):
    monkeypatch.setattr(
        ops_services,
        "load_dashboard_inputs",
        lambda: {
            "source_counts": [],
            "total_postings": 0,
            "recent_runs": [],
        },
    )
    monkeypatch.setattr(ops_services, "load_recent_ingestion_runs", lambda: [])
    monkeypatch.setattr(
        ops_services,
        "load_extraction_health_inputs",
        lambda: {
            "top_skills": [],
            "empty_extractions": [],
        },
    )


def test_ops_routes_return_200(client, monkeypatch):
    patch_empty_loaders(monkeypatch)

    for path in ["/", "/ingestion-runs", "/extraction-health"]:
        response = client.get(path)
        assert response.status_code == 200


def test_dashboard_aggregates_seeded_fixture_data(client, monkeypatch):
    started_at = datetime(2026, 8, 5, 20, 0, tzinfo=UTC)
    completed_at = datetime(2026, 8, 5, 20, 2, tzinfo=UTC)
    monkeypatch.setattr(
        ops_services,
        "load_dashboard_inputs",
        lambda: {
            "source_counts": [
                {"source": "greenhouse", "count": 2},
                {"source": "ashby", "count": 1},
            ],
            "total_postings": 3,
            "recent_runs": [
                {
                    "source_type": "canada_jobs_fetch",
                    "status": "succeeded",
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "duration_seconds": 120.0,
                    "duration_label": "2.0m",
                    "raw_job_count": 4,
                    "processed_job_count": 3,
                    "successful_sources": 2,
                    "total_sources": 2,
                    "run_metadata": {"dedup_rejected_count": 1},
                    "source_results": [],
                }
            ],
        },
    )

    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Total postings" in body
    assert ">3<" in body
    assert "greenhouse" in body
    assert "ashby" in body
    assert "Dedup rejected" in body
    assert ">1<" in body
    assert "2026-08-05 20:02" in body


def test_ingestion_runs_render_source_breakdown(client, monkeypatch):
    monkeypatch.setattr(
        ops_services,
        "load_recent_ingestion_runs",
        lambda: [
            {
                "source_type": "canada_jobs_fetch",
                "status": "partial_success",
                "started_at": datetime(2026, 8, 5, 20, 0, tzinfo=UTC),
                "completed_at": datetime(2026, 8, 5, 20, 1, tzinfo=UTC),
                "duration_label": "1.0m",
                "raw_job_count": 5,
                "processed_job_count": 4,
                "successful_sources": 1,
                "total_sources": 2,
                "source_results": [
                    {
                        "company": "Example",
                        "source_type": "greenhouse",
                        "status": "succeeded",
                        "job_count": 4,
                    }
                ],
            }
        ],
    )

    response = client.get("/ingestion-runs")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "canada_jobs_fetch" in body
    assert "partial_success" in body
    assert "Example" in body
    assert "greenhouse" in body


def test_extraction_health_renders_empty_extraction_rows(client, monkeypatch):
    monkeypatch.setattr(
        ops_services,
        "load_extraction_health_inputs",
        lambda: {
            "top_skills": [{"skill": "Python", "count": 7}],
            "empty_extractions": [
                {
                    "title": "Data Engineer",
                    "company": "Example",
                    "source": "greenhouse",
                    "source_url": "https://example.com/jobs/empty",
                    "provider": "deterministic_fallback",
                    "error": "Groq attempt 2: returned no skills",
                    "created_at": datetime(2026, 8, 5, 20, 2, tzinfo=UTC),
                }
            ],
        },
    )

    response = client.get("/extraction-health")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Python" in body
    assert "Data Engineer" in body
    assert "returned no skills" in body


def test_empty_state_rendering(client, monkeypatch):
    patch_empty_loaders(monkeypatch)

    dashboard_body = client.get("/").get_data(as_text=True)
    runs_body = client.get("/ingestion-runs").get_data(as_text=True)
    extraction_body = client.get("/extraction-health").get_data(as_text=True)

    assert "No postings are available yet." in dashboard_body
    assert "No ingestion runs have been recorded yet." in runs_body
    assert "No extracted skills have been persisted yet." in extraction_body
    assert "No empty extraction results found." in extraction_body
