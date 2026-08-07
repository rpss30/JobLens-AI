from __future__ import annotations

import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "backup_database.sh"
VERIFY_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "verify_database_backup.sh"
RESTORE_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "restore_database.sh"
STATUS_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_database_backup_status.sh"
SYSTEMD_SERVICE = ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-db-backup.service"
SYSTEMD_TIMER = ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-db-backup.timer"
BACKUP_DOC = ROOT_DIR / "docs" / "database-backups.md"
README_PATH = ROOT_DIR / "README.md"
PRODUCTION_DEPLOYMENT_DOC = ROOT_DIR / "docs" / "production-deployment.md"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_database_backup_scripts_are_executable_and_valid_bash() -> None:
    for script_path in [BACKUP_SCRIPT, VERIFY_SCRIPT, RESTORE_SCRIPT, STATUS_SCRIPT]:
        assert script_path.stat().st_mode & stat.S_IXUSR
        subprocess.run(["bash", "-n", str(script_path)], check=True)


def test_backup_script_uses_custom_pg_dump_with_retention_and_status_manifest() -> None:
    script = read_file(BACKUP_SCRIPT)

    assert "pg_dump" in script
    assert "--format=custom" in script
    assert "--compress=${BACKUP_COMPRESS_LEVEL}" in script
    assert "--no-owner" in script
    assert "--no-privileges" in script
    assert "latest_backup.json" in script
    assert '"status": "%s"' in script
    assert "write_manifest \"failed\"" in script
    assert "write_manifest \"succeeded\"" in script
    assert "sha256sum" in script
    assert "shasum -a 256" in script
    assert "BACKUP_RETENTION_DAYS" in script
    assert "BACKUP_RETENTION_COUNT" in script
    assert "find \"${BACKUP_DIR}\"" in script
    assert "-mtime \"+${BACKUP_RETENTION_DAYS}\"" in script
    assert "tail -n \"+$((BACKUP_RETENTION_COUNT + 1))\"" in script


def test_verify_script_restores_backup_into_temporary_database() -> None:
    script = read_file(VERIFY_SCRIPT)

    assert "BACKUP_FILE" in script
    assert "RESTORE_VERIFY_DATABASE" in script
    assert "joblens_restore_check_" in script
    assert "createdb -U" in script
    assert "pg_restore -U" in script
    assert "--exit-on-error" in script
    assert "information_schema.tables" in script
    assert "dropdb -U" in script
    assert "KEEP_RESTORE_CHECK_DATABASE" in script


def test_restore_script_is_dry_run_gated_and_verifies_before_overwrite() -> None:
    script = read_file(RESTORE_SCRIPT)

    assert "DRY_RUN" in script
    assert "Dry run only" in script
    assert "CONFIRM_RESTORE=yes" in script
    assert "Refusing to restore without CONFIRM_RESTORE=yes" in script
    assert "verify_database_backup.sh" in script
    assert "SKIP_RESTORE_VERIFY" in script
    assert "compose stop dashboard api django-ops" in script
    assert "pg_restore -U" in script
    assert "--clean --if-exists" in script
    assert "--exit-on-error" in script
    assert "compose up -d" in script
    assert "check_production_health.sh" in script


def test_backup_status_script_detects_failed_missing_or_stale_backups() -> None:
    script = read_file(STATUS_SCRIPT)

    assert "latest_backup.json" in script
    assert "BACKUP_MAX_AGE_HOURS" in script
    assert '"status": "succeeded"' in script
    assert "Backup status file is missing" in script
    assert "Latest backup did not succeed" in script
    assert "Latest successful backup is stale" in script
    assert "stat -c %Y" in script
    assert "stat -f %m" in script


def test_systemd_timer_runs_backup_service_daily_with_retention_defaults() -> None:
    service = read_file(SYSTEMD_SERVICE)
    timer = read_file(SYSTEMD_TIMER)

    assert "Type=oneshot" in service
    assert "User=joblens" in service
    assert "WorkingDirectory=/srv/joblens-ai" in service
    assert "BACKUP_DIR=/srv/joblens-backups" in service
    assert "BACKUP_RETENTION_DAYS=14" in service
    assert "BACKUP_RETENTION_COUNT=14" in service
    assert "ExecStart=/srv/joblens-ai/deploy/scripts/backup_database.sh" in service
    assert "OnCalendar=*-*-* 03:15:00" in timer
    assert "Persistent=true" in timer
    assert "RandomizedDelaySec=900" in timer


def test_database_backup_files_do_not_create_cloud_resources() -> None:
    combined = "\n".join(
        read_file(path)
        for path in [
            BACKUP_SCRIPT,
            VERIFY_SCRIPT,
            RESTORE_SCRIPT,
            STATUS_SCRIPT,
            SYSTEMD_SERVICE,
            SYSTEMD_TIMER,
        ]
    ).lower()

    forbidden_commands = [
        "terraform apply",
        "aws lightsail create-instances",
        "aws s3 cp",
        "aws ecs create-service",
        "aws rds create-db-instance",
        "aws elbv2 create-load-balancer",
        "aws ec2 create-nat-gateway",
    ]

    for command in forbidden_commands:
        assert command not in combined


def test_database_backup_documentation_covers_restore_and_operational_limits() -> None:
    doc = read_file(BACKUP_DOC).lower()
    readme = read_file(README_PATH)
    deployment_doc = read_file(PRODUCTION_DEPLOYMENT_DOC)

    expected_topics = [
        "pg_dump",
        "custom-format",
        "latest_backup.json",
        "sha-256",
        "retention",
        "systemd",
        "restore test",
        "temporary database",
        "confirm_restore=yes",
        "dry_run=no",
        "no cloud resources",
        "no s3 upload",
        "off-server storage",
    ]

    for topic in expected_topics:
        assert topic in doc

    assert "docs/database-backups.md" in readme
    assert "database-backups.md" in deployment_doc
