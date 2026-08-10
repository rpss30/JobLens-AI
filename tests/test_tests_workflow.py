from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/tests.yml")
STACK_WORKFLOW_PATH = Path(".github/workflows/stack-check.yml")


def test_tests_workflow_runs_pytest_with_coverage() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python -m pytest -q --cov=src" in workflow_text
    assert "--cov-report=term-missing" in workflow_text
    assert "--cov-report=xml" in workflow_text


def test_tests_workflow_uploads_coverage_artifact() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "actions/upload-artifact@v4" in workflow_text
    assert "coverage.xml" in workflow_text


def test_stack_check_workflow_boots_the_production_stack_on_pull_requests() -> None:
    workflow_text = STACK_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "pull_request:" in workflow_text
    assert 'docker-compose.prod.yml' in workflow_text

    # The same migration order the deploy runs, then every healthcheck must pass.
    assert "alembic upgrade head" in workflow_text
    assert "django_ops.manage migrate" in workflow_text
    assert "up -d --wait" in workflow_text

    # Public routes are exercised through Caddy, including the browser-facing
    # handler that a reverse-proxied /api/* prefix would otherwise shadow.
    for path in ["/healthz", "/proxy/health", "/api/health", "/ops/login/"]:
        assert path in workflow_text

    assert "/proxy/analyze" in workflow_text
    assert "Request body must be valid JSON." in workflow_text
