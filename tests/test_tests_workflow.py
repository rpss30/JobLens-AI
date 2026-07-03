from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/tests.yml")


def test_tests_workflow_runs_pytest_with_coverage() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "python -m pytest -q --cov=src" in workflow_text
    assert "--cov-report=term-missing" in workflow_text
    assert "--cov-report=xml" in workflow_text


def test_tests_workflow_uploads_coverage_artifact() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "actions/upload-artifact@v4" in workflow_text
    assert "coverage.xml" in workflow_text
