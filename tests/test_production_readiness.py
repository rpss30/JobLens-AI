from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
READINESS_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_production_readiness.sh"
GITIGNORE = ROOT_DIR / ".gitignore"
READINESS_DOC = ROOT_DIR / "docs" / "production-readiness.md"
README_PATH = ROOT_DIR / "README.md"
PRODUCTION_DEPLOYMENT_DOC = ROOT_DIR / "docs" / "production-deployment.md"
PRODUCTION_COMPOSE_DOC = ROOT_DIR / "docs" / "production-compose.md"
SECURITY_DOC = ROOT_DIR / "docs" / "security.md"
LIGHTSAIL_DOC = ROOT_DIR / "docs" / "lightsail-deployment-plan.md"
LIGHTSAIL_PLAN = ROOT_DIR / "deploy" / "lightsail" / "resource-plan.example.json"


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
        ".github/workflows/security-scan.yml",
        ".github/workflows/uptime-check.yml",
        "docs/production-compose.md",
        "docs/production-deployment.md",
        "docs/server-hardening.md",
        "docs/database-backups.md",
        "docs/operations-monitoring.md",
        "docs/offsite-backups-alerts.md",
        "docs/parameter-store-secrets.md",
        "docs/secret-rotation.md",
        "docs/security.md",
        "docs/security-scanning.md",
        "docs/external-uptime-monitoring.md",
        "docs/lightsail-deployment-plan.md",
        "deploy/lightsail/resource-plan.example.json",
        "deploy/lightsail/terraform/README.md",
        "deploy/lightsail/terraform/main.tf",
        "deploy/lightsail/terraform/outputs.tf",
        "deploy/lightsail/terraform/terraform.tfvars.example",
        "deploy/lightsail/terraform/variables.tf",
        "deploy/lightsail/terraform/versions.tf",
        "docs/production-ingestion.md",
        "deploy/server/systemd/joblens-ingestion-refresh.service",
        "deploy/server/systemd/joblens-ingestion-refresh.timer",
        "deploy/scripts/deploy_production.sh",
        "deploy/scripts/rollback_production.sh",
        "deploy/scripts/check_production_health.sh",
        "deploy/scripts/backup_database.sh",
        "deploy/scripts/verify_database_backup.sh",
        "deploy/scripts/check_database_backup_status.sh",
        "deploy/scripts/upload_database_backup.sh",
        "deploy/scripts/check_offsite_backup_status.sh",
        "deploy/scripts/send_operations_alert.sh",
        "deploy/scripts/check_operations_status.sh",
        "deploy/scripts/check_disk_usage.sh",
        "deploy/scripts/audit_secret_configuration.sh",
        "deploy/scripts/render_env_from_parameter_store.sh",
        "deploy/scripts/run_security_scans.sh",
        "deploy/scripts/check_external_uptime.sh",
        "deploy/scripts/run_ingestion_refresh.sh",
        "deploy/scripts/check_ingestion_refresh_status.sh",
    ]

    for path in required_paths:
        assert path in script

    assert "RUN_COMPOSE_CONFIG" in script
    assert "RUN_SECRET_AUDIT" in script
    assert "RUN_PARAMETER_STORE_RENDER_CHECK" in script
    assert "RUN_BACKUP_STATUS_CHECK" in script
    assert "RUN_OFFSITE_BACKUP_STATUS_CHECK" in script
    assert "RUN_OPERATIONS_STATUS_CHECK" in script
    assert "RUN_TERRAFORM_VALIDATE" in script
    assert "STRICT_READINESS" in script
    assert "check_production_readiness.sh" in script


def test_readiness_generated_output_is_ignored() -> None:
    gitignore = read_file(GITIGNORE)

    assert "deploy/readiness/" in gitignore
    assert "deploy/ingestion/" in gitignore
    assert "deploy/lightsail/production-inventory.json" in gitignore
    assert "deploy/lightsail/deployment-evidence/" in gitignore
    assert "deploy/lightsail/terraform/.terraform/" in gitignore
    assert "deploy/lightsail/terraform/*.tfplan" in gitignore
    assert "deploy/lightsail/terraform/*.tfstate" in gitignore
    assert "deploy/lightsail/terraform/terraform.tfvars" in gitignore
    assert "deploy/security-reports/" in gitignore
    assert "deploy/uptime-reports/" in gitignore

    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "deploy/readiness/latest_readiness.json",
            "deploy/ingestion/latest_ingestion_refresh.json",
            "deploy/security-reports/latest_security_scan.json",
            "deploy/uptime-reports/latest_uptime_check.json",
        ],
        check=True,
        capture_output=True,
        cwd=ROOT_DIR,
        text=True,
    )

    assert "deploy/readiness/latest_readiness.json" in ignored.stdout
    assert "deploy/ingestion/latest_ingestion_refresh.json" in ignored.stdout
    assert "deploy/security-reports/latest_security_scan.json" in ignored.stdout
    assert "deploy/uptime-reports/latest_uptime_check.json" in ignored.stdout

    ignored_lightsail = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "deploy/lightsail/production-inventory.json",
            "deploy/lightsail/deployment-evidence/example.json",
            "deploy/lightsail/terraform/.terraform/example",
            "deploy/lightsail/terraform/terraform.tfvars",
            "deploy/lightsail/terraform/reviewed.tfplan",
            "deploy/lightsail/terraform/terraform.tfstate",
        ],
        check=True,
        capture_output=True,
        cwd=ROOT_DIR,
        text=True,
    )

    assert "deploy/lightsail/production-inventory.json" in ignored_lightsail.stdout
    assert "deploy/lightsail/deployment-evidence/example.json" in ignored_lightsail.stdout
    assert "deploy/lightsail/terraform/.terraform/example" in ignored_lightsail.stdout
    assert "deploy/lightsail/terraform/terraform.tfvars" in ignored_lightsail.stdout
    assert "deploy/lightsail/terraform/reviewed.tfplan" in ignored_lightsail.stdout
    assert "deploy/lightsail/terraform/terraform.tfstate" in ignored_lightsail.stdout


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
    assert "deploy/scripts/render_env_from_parameter_store.sh" in script
    assert "deploy/scripts/run_security_scans.sh" in script
    assert "deploy/scripts/check_external_uptime.sh" in script
    assert "deploy/scripts/check_database_backup_status.sh" in script
    assert "deploy/scripts/check_offsite_backup_status.sh" in script
    assert "deploy/scripts/check_operations_status.sh" in script
    assert "deploy/scripts/run_ingestion_refresh.sh" in script
    assert "deploy/scripts/check_ingestion_refresh_status.sh" in script


def test_production_readiness_documentation_covers_rollout_gates() -> None:
    doc = read_file(READINESS_DOC).lower()
    readme = read_file(README_PATH)
    deployment_doc = read_file(PRODUCTION_DEPLOYMENT_DOC)
    compose_doc = read_file(PRODUCTION_COMPOSE_DOC)
    security_doc = read_file(SECURITY_DOC)

    expected_topics = [
        "check_production_readiness.sh",
        "strict_readiness=true",
        "cost and approval gate",
        "aws budget",
        "billing alerts",
        "server preconditions",
        "network and dns preconditions",
        "secret preconditions",
        "parameter store",
        "security scans",
        "external uptime",
        "database preconditions",
        "deployment preconditions",
        "post-deploy verification",
        "ready definition",
        "off-server backup",
        "alert delivery",
        "no cloud resource has been provisioned",
        "lightsail-deployment-plan.md",
        "deploy/lightsail/resource-plan.example.json",
        "terraform template",
        "no terraform state",
        "private inventory",
        "scheduled ingestion",
        "ingestion refresh status",
        "require approval",
        "offsite-backups-alerts.md",
        "parameter-store-secrets.md",
        "security-scanning.md",
        "external-uptime-monitoring.md",
    ]

    for topic in expected_topics:
        assert topic in doc

    assert "docs/production-readiness.md" in readme
    assert "docs/lightsail-deployment-plan.md" in readme
    assert "docs/production-ingestion.md" in readme
    assert "production-readiness.md" in deployment_doc
    assert "production-readiness.md" in compose_doc
    assert "production-readiness.md" in security_doc
    assert LIGHTSAIL_DOC.exists()
    assert LIGHTSAIL_PLAN.exists()
