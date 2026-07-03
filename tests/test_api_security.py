from fastapi.testclient import TestClient

from src.api.application import create_app
from src.api.security import analyze_rate_limiter, get_cors_origins


def test_cors_origins_default_to_local_dashboard_hosts(monkeypatch) -> None:
    monkeypatch.delenv("JOBLENS_CORS_ORIGINS", raising=False)

    assert "http://localhost:8501" in get_cors_origins()
    assert "http://127.0.0.1:8502" in get_cors_origins()


def test_cors_origins_can_be_configured_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "JOBLENS_CORS_ORIGINS",
        "https://joblens.example.com, https://dashboard.example.com",
    )

    assert get_cors_origins() == [
        "https://joblens.example.com",
        "https://dashboard.example.com",
    ]


def test_api_allows_configured_cors_preflight(monkeypatch) -> None:
    monkeypatch.setenv("JOBLENS_CORS_ORIGINS", "https://joblens.example.com")
    client = TestClient(create_app())

    response = client.options(
        "/analyze",
        headers={
            "Origin": "https://joblens.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "https://joblens.example.com"
    )


def test_analyze_endpoint_rate_limits_expensive_requests(monkeypatch) -> None:
    monkeypatch.setenv("JOBLENS_ANALYZE_RATE_LIMIT", "1")
    monkeypatch.setenv("JOBLENS_RATE_LIMIT_WINDOW_SECONDS", "60")
    analyze_rate_limiter.clear()
    client = TestClient(create_app())
    payload = {
        "current_skills": ["Python"],
        "target_roles": ["Data Scientist"],
        "location": "Any",
        "experience_level": "Any",
    }

    first_response = client.post("/analyze", json=payload)
    second_response = client.post("/analyze", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert "Rate limit exceeded" in second_response.json()["detail"]

    analyze_rate_limiter.clear()


def test_analyze_endpoint_rejects_oversized_skill_list() -> None:
    client = TestClient(create_app())
    payload = {
        "current_skills": [f"skill-{index}" for index in range(51)],
        "target_roles": ["Data Scientist"],
        "location": "Any",
        "experience_level": "Any",
    }

    response = client.post("/analyze", json=payload)

    assert response.status_code == 422


def test_analyze_endpoint_rejects_oversized_skill_value() -> None:
    client = TestClient(create_app())
    payload = {
        "current_skills": ["x" * 81],
        "target_roles": ["Data Scientist"],
        "location": "Any",
        "experience_level": "Any",
    }

    response = client.post("/analyze", json=payload)

    assert response.status_code == 422
