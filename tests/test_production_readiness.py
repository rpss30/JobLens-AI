from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
READINESS_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_production_readiness.sh"
GITIGNORE = ROOT_DIR / ".gitignore"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_readiness(tmp_path: Path, **env_overrides: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    status_file = tmp_path / "readiness.json"
    env = {
        **os.environ,
        "READINESS_STATUS_FILE": str(status_file),
        **env_overrides,
    }

    result = subprocess.run(
        [str(READINESS_SCRIPT)],
        check=False,
        capture_output=True,
        cwd=ROOT_DIR,
        env=env,
        text=True,
    )

    return result, json.loads(status_file.read_text(encoding="utf-8"))


def test_readiness_script_is_executable_and_valid_bash() -> None:
    assert READINESS_SCRIPT.stat().st_mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(READINESS_SCRIPT)], check=True)


def test_readiness_script_reports_warning_without_local_production_env(tmp_path: Path) -> None:
    result, payload = run_readiness(tmp_path)

    assert result.returncode == 0
    assert payload["status"] == "warning"
    assert payload["failure_count"] == 0
    assert payload["warning_count"] == 1
    assert "Production readiness warning" in result.stdout

    checks_by_name = {check["name"]: check for check in payload["checks"]}

    assert checks_by_name["env-file:.env.production"]["status"] == "warning"
    assert checks_by_name["cloud-provisioning"]["status"] == "ok"
    assert checks_by_name["compose-config"]["status"] == "skipped"
    assert checks_by_name["secret-audit"]["status"] == "skipped"
    assert checks_by_name["backup-status"]["status"] == "skipped"
    assert checks_by_name["operations-status"]["status"] == "skipped"


def test_readiness_script_strict_mode_fails_on_warnings(tmp_path: Path) -> None:
    result, payload = run_readiness(tmp_path, STRICT_READINESS="true")

    assert result.returncode == 1
    assert payload["status"] == "warning"
    assert payload["failure_count"] == 0
    assert payload["warning_count"] == 1


def test_readiness_script_tracks_required_files_scripts_and_ignored_outputs() -> None:
    script = read_file(READINESS_SCRIPT)

    required_paths = [
        "docker-compose.prod.yml",
        ".env.production.example",
        "deploy/caddy/Caddyfile",
        ".github/workflows/deploy-production.yml",
        "docs/production-compose.md",
        "docs/production-deployment.md",
        "docs/server-hardening.md",
        "docs/database-backups.md",
        "docs/operations-monitoring.md",
        "docs/secret-rotation.md",
        "docs/security.md",
        "deploy/scripts/deploy_production.sh",
        "deploy/scripts/rollback_production.sh",
        "deploy/scripts/check_production_health.sh",
        "deploy/scripts/backup_database.sh",
        "deploy/scripts/verify_database_backup.sh",
        "deploy/scripts/check_database_backup_status.sh",
        "deploy/scripts/check_operations_status.sh",
        "deploy/scripts/check_disk_usage.sh",
        "deploy/scripts/audit_secret_configuration.sh",
    ]

    for path in required_paths:
        assert path in script

    assert "RUN_COMPOSE_CONFIG" in script
    assert "RUN_SECRET_AUDIT" in script
    assert "RUN_BACKUP_STATUS_CHECK" in script
    assert "RUN_OPERATIONS_STATUS_CHECK" in script
    assert "STRICT_READINESS" in script
    assert "check_production_readiness.sh" in script


def test_readiness_generated_output_is_ignored() -> None:
    gitignore = read_file(GITIGNORE)

    assert "deploy/readiness/" in gitignore

    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "deploy/readiness/latest_readiness.json"],
        check=True,
        capture_output=True,
        cwd=ROOT_DIR,
        text=True,
    )

    assert "deploy/readiness/latest_readiness.json" in ignored.stdout


def test_readiness_script_does_not_execute_cloud_provisioning() -> None:
    script = read_file(READINESS_SCRIPT).lower()

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
        assert command in script

    assert "! -name \"check_production_readiness.sh\"" in script
    assert "docker compose --env-file .env.production.example" in script
    assert "deploy/scripts/audit_secret_configuration.sh" in script
    assert "deploy/scripts/check_database_backup_status.sh" in script
    assert "deploy/scripts/check_operations_status.sh" in script
