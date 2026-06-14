from fastapi.testclient import TestClient

from src.api.main import app


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