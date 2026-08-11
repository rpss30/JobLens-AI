from pathlib import Path


import json


WORKFLOW_PATH = Path(".github/workflows/tests.yml")
STACK_WORKFLOW_PATH = Path(".github/workflows/stack-check.yml")
FRONTEND_WORKFLOW_PATH = Path(".github/workflows/frontend-checks.yml")
FRONTEND_PACKAGE_JSON = Path("frontend/package.json")


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


def test_frontend_checks_workflow_lints_and_typechecks_the_frontend() -> None:
    workflow_text = FRONTEND_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "pull_request:" in workflow_text
    assert "npm ci" in workflow_text
    assert "npm run lint" in workflow_text
    assert "npm run typecheck" in workflow_text
    assert "npm test" in workflow_text

    # Matches the node:24-alpine base image the production frontend runs on.
    assert 'node-version: "24"' in workflow_text


def test_frontend_typecheck_regenerates_route_types_from_scratch() -> None:
    """Route and layout prop types are generated, not committed.

    PageProps and LayoutProps come from .next/types, which is gitignored, so a
    bare `tsc --noEmit` fails on a clean checkout. `next typegen` also leaves
    types behind for routes that have since moved, so the stale directory has to
    be cleared first or a local run fails on files no longer in the app.
    """
    scripts = json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]
    typecheck = scripts["typecheck"]

    assert "rmSync('.next/types'" in typecheck
    assert typecheck.index("rmSync") < typecheck.index("next typegen")
    assert typecheck.endswith("tsc --noEmit")


def test_frontend_package_exposes_a_test_script() -> None:
    scripts = json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]

    assert scripts["test"] == "vitest run"
