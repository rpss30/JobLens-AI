from __future__ import annotations

import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
HEALTH_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_production_health.sh"
DEPLOY_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "deploy_production.sh"
ROLLBACK_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "rollback_production.sh"
WORKFLOW_PATH = ROOT_DIR / ".github" / "workflows" / "deploy-production.yml"
DEPLOYMENT_DOC = ROOT_DIR / "docs" / "production-deployment.md"
README_PATH = ROOT_DIR / "README.md"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_deployment_scripts_are_executable_and_valid_bash() -> None:
    for script_path in [HEALTH_SCRIPT, DEPLOY_SCRIPT, ROLLBACK_SCRIPT]:
        assert script_path.stat().st_mode & stat.S_IXUSR
        subprocess.run(["bash", "-n", str(script_path)], check=True)


def test_deploy_script_runs_safe_migration_sequence_before_restart() -> None:
    script = read_file(DEPLOY_SCRIPT)

    for required_env in ["DEPLOY_HOST", "DEPLOY_USER", "DEPLOY_PATH"]:
        assert f"require_env {required_env}" in script

    assert "StrictHostKeyChecking=accept-new" in script
    assert "printf '%s\\n' \"${previous_revision}\" > .deploy/previous_revision" in script
    assert "git fetch --prune origin" in script
    assert 'git checkout --force "${DEPLOY_REF}"' in script
    assert "docker-compose.prod.yml config -q" in script

    build_index = script.index("docker-compose.prod.yml build")
    db_index = script.index("docker-compose.prod.yml up -d db")
    alembic_index = script.index("run --rm -T api alembic upgrade head")
    django_index = script.index(
        "run --rm -T django-ops python -m django_ops.manage migrate",
    )
    roles_index = script.index(
        "run --rm -T django-ops python -m django_ops.manage bootstrap_ops_roles",
    )
    restart_index = script.index('docker-compose.prod.yml up -d\n')

    assert build_index < db_index < alembic_index < django_index < roles_index
    assert roles_index < restart_index

    # Disk cleanup runs after the stack is up and never fails the deploy, so a
    # full disk cannot accumulate across automatic deploys.
    prune_index = script.index("docker image prune -f")

    assert restart_index < prune_index
    assert "docker image prune -f || true" in script
    assert "docker builder prune -f --filter until=168h || true" in script


def test_deploy_script_does_not_let_compose_consume_the_piped_script() -> None:
    """The remote block arrives on stdin, so a container attached to stdin eats it.

    Without this, the deploy stopped silently after the first migration and still
    exited 0, leaving freshly built images that were never started.
    """
    script = read_file(DEPLOY_SCRIPT)

    assert "bash -s" in script

    compose_run_lines = [
        line
        for line in script.splitlines()
        if "compose" in line and "run --rm" in line
    ]

    assert compose_run_lines

    for line in compose_run_lines:
        assert "run --rm -T" in line, line
        assert line.rstrip().endswith("< /dev/null"), line

    # Truncation is invisible to the health checks, which pass against the old
    # containers, so the remote block has to prove it reached the end.
    assert 'echo "REMOTE_DEPLOY_COMPLETE"' in script
    assert "grep -q '^REMOTE_DEPLOY_COMPLETE$'" in script


def test_rollback_script_restarts_without_database_downgrades() -> None:
    script = read_file(ROLLBACK_SCRIPT)

    assert "DEPLOY_ROLLBACK_REF" in script
    assert ".deploy/previous_revision" in script
    assert 'git checkout --force "${rollback_ref}"' in script
    assert "docker-compose.prod.yml build" in script
    assert 'docker-compose.prod.yml up -d\n' in script
    assert "Database migrations were not downgraded automatically." in script
    assert "alembic downgrade" not in script
    assert "django_ops.manage migrate" not in script


def test_health_script_checks_edge_api_and_operations_routes() -> None:
    script = read_file(HEALTH_SCRIPT)

    assert "JOBLENS_HEALTH_BASE_URL" in script
    assert "JOBLENS_DOMAIN" in script
    assert 'check_url "/healthz"' in script
    assert 'check_url "/proxy/health"' in script
    assert 'check_url "/api/health"' in script
    assert 'check_url "/ops/login/"' in script
    assert "HEALTH_RETRIES" in script
    assert "HEALTH_DELAY_SECONDS" in script


def test_deployment_workflow_is_test_gated_environment_protected_and_rollback_ready() -> None:
    workflow = read_file(WORKFLOW_PATH)

    assert "workflow_dispatch:" in workflow

    # Pushes to main deploy automatically, except documentation-only pushes,
    # and never before the test suite passes.
    assert "push:" in workflow
    assert "paths-ignore:" in workflow
    assert '- "**/*.md"' in workflow
    assert "needs: test" in workflow
    assert "python -m pytest -q" in workflow

    # A push-triggered run has no workflow inputs to read.
    assert "inputs.deploy_ref || 'origin/main'" in workflow
    assert "inputs.skip_public_health_check || 'false'" in workflow
    assert "environment: production" in workflow
    assert "concurrency:" in workflow
    assert "group: production-deployment" in workflow
    assert "bash -n deploy/scripts/deploy_production.sh" in workflow
    assert "id: deploy" in workflow
    assert "deploy/scripts/deploy_production.sh" in workflow
    assert "if: failure() && steps.deploy.outcome == 'failure'" in workflow
    assert "deploy/scripts/rollback_production.sh" in workflow

    required_secrets = [
        "PRODUCTION_SSH_HOST",
        "PRODUCTION_SSH_USER",
        "PRODUCTION_DEPLOY_PATH",
        "PRODUCTION_SSH_KEY",
        "PRODUCTION_DOMAIN",
    ]

    for secret_name in required_secrets:
        assert f"secrets.{secret_name}" in workflow


def test_deployment_automation_does_not_provision_cloud_resources() -> None:
    combined = "\n".join(
        read_file(path)
        for path in [HEALTH_SCRIPT, DEPLOY_SCRIPT, ROLLBACK_SCRIPT, WORKFLOW_PATH]
    ).lower()

    forbidden_commands = [
        "terraform apply",
        "aws lightsail create-instances",
        "aws ecs create-service",
        "aws rds create-db-instance",
        "aws elbv2 create-load-balancer",
        "aws ec2 create-nat-gateway",
        "aws route53 create-hosted-zone",
    ]

    for command in forbidden_commands:
        assert command not in combined


def test_production_deployment_documentation_covers_required_operations() -> None:
    doc = read_file(DEPLOYMENT_DOC).lower()
    readme = read_file(README_PATH)

    expected_topics = [
        "already-provisioned server",
        "github actions",
        "production_ssh_host",
        "production_ssh_key",
        "alembic upgrade head",
        "django_ops.manage migrate",
        "bootstrap_ops_roles",
        "rollback",
        "no database downgrades",
        "no cloud resources",
        "health checks",
    ]

    for topic in expected_topics:
        assert topic in doc

    assert "docs/production-deployment.md" in readme
