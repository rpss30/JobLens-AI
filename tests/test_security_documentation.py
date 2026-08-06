from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_security_documentation_covers_core_controls() -> None:
    security_doc = (PROJECT_ROOT / "docs" / "security.md").read_text()
    normalized_doc = security_doc.lower()

    expected_topics = [
        "joblens_cors_origins",
        "joblens_analyze_rate_limit",
        "cors allowlist",
        "rate limiter",
        "raw resume text",
        "2 mb",
        "5,000 rows",
        "aws secrets manager",
        "least",
        "django operations portal",
        "csrf",
        "samesite",
    ]

    for topic in expected_topics:
        assert topic in normalized_doc


def test_security_environment_template_lists_runtime_controls() -> None:
    env_template = (PROJECT_ROOT / ".env.example").read_text()

    expected_variables = [
        "JOBLENS_CORS_ORIGINS=",
        "JOBLENS_RATE_LIMIT_ENABLED=",
        "JOBLENS_ANALYZE_RATE_LIMIT=",
        "JOBLENS_RATE_LIMIT_WINDOW_SECONDS=",
        "DJANGO_SECRET_KEY=",
        "DJANGO_ALLOWED_HOSTS=",
        "DJANGO_SESSION_COOKIE_SECURE=",
        "DJANGO_CSRF_COOKIE_SECURE=",
    ]

    for variable in expected_variables:
        assert variable in env_template


def test_readme_links_security_documentation() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert "docs/security.md" in readme
    assert "API security controls" in readme
