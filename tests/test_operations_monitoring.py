from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DISK_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_disk_usage.sh"
STATUS_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_operations_status.sh"
LOG_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "collect_operations_logs.sh"
MONITOR_SERVICE = ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-ops-monitor.service"
MONITOR_TIMER = ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-ops-monitor.timer"
GITIGNORE = ROOT_DIR / ".gitignore"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_operations_monitoring_scripts_are_executable_and_valid_bash() -> None:
    for script_path in [DISK_SCRIPT, STATUS_SCRIPT, LOG_SCRIPT]:
        assert script_path.stat().st_mode & stat.S_IXUSR
        subprocess.run(["bash", "-n", str(script_path)], check=True)


def test_disk_check_passes_for_root_path_with_high_thresholds() -> None:
    result = subprocess.run(
        [str(DISK_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "DISK_PATHS": "/",
            "DISK_WARN_PERCENT": "95",
            "DISK_CRITICAL_PERCENT": "99",
        },
        text=True,
    )

    assert "ok disk usage: /" in result.stdout


def test_operations_status_writes_json_when_checks_are_skipped(tmp_path: Path) -> None:
    status_file = tmp_path / "latest_status.json"

    result = subprocess.run(
        [str(STATUS_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "MONITOR_STATUS_FILE": str(status_file),
            "SKIP_COMPOSE_CHECK": "true",
            "SKIP_PUBLIC_HEALTH_CHECK": "true",
            "SKIP_BACKUP_STATUS_CHECK": "true",
            "SKIP_DISK_CHECK": "true",
        },
        text=True,
    )

    payload = json.loads(status_file.read_text(encoding="utf-8"))

    assert "Operations status ok" in result.stdout
    assert payload["status"] == "ok"
    assert [check["name"] for check in payload["checks"]] == [
        "compose_services",
        "public_health",
        "database_backup",
        "disk_usage",
    ]
    assert {check["status"] for check in payload["checks"]} == {"skipped"}


def test_operations_status_checks_compose_health_backup_and_disk_state() -> None:
    script = read_file(STATUS_SCRIPT)

    assert "EXPECTED_SERVICES" in script
    assert "caddy dashboard api django-ops db" in script
    assert "compose ps --status running --services" in script
    assert "check_production_health.sh" in script
    assert "check_database_backup_status.sh" in script
    assert "check_disk_usage.sh" in script
    assert "MONITOR_STATUS_FILE" in script
    assert '"checks": [' in script
    assert "SKIP_PUBLIC_HEALTH_CHECK" in script


def test_log_collection_captures_compose_logs_and_optional_systemd_context() -> None:
    script = read_file(LOG_SCRIPT)

    assert "compose ps >" in script
    assert "compose logs --timestamps --tail" in script
    assert "LOG_SERVICES" in script
    assert "caddy dashboard api django-ops db" in script
    assert "manifest.json" in script
    assert "INCLUDE_SYSTEMD_LOGS" in script
    assert "journalctl" in script
    assert "joblens-ops-monitor.service" in script
    assert "joblens-db-backup.service" in script


def test_monitoring_timer_runs_every_five_minutes_with_server_defaults() -> None:
    service = read_file(MONITOR_SERVICE)
    timer = read_file(MONITOR_TIMER)

    assert "Type=oneshot" in service
    assert "User=joblens" in service
    assert "WorkingDirectory=/srv/joblens-ai" in service
    assert "BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json" in service
    assert "BACKUP_MAX_AGE_HOURS=30" in service
    assert "DISK_WARN_PERCENT=80" in service
    assert "DISK_CRITICAL_PERCENT=90" in service
    assert "SKIP_PUBLIC_HEALTH_CHECK=true" in service
    assert "MONITOR_STATUS_FILE=/srv/joblens-monitoring/latest_status.json" in service
    assert "ExecStart=/srv/joblens-ai/deploy/scripts/check_operations_status.sh" in service
    assert "OnCalendar=*:0/5" in timer
    assert "Persistent=true" in timer
    assert "RandomizedDelaySec=30" in timer


def test_generated_operations_outputs_are_ignored() -> None:
    gitignore = read_file(GITIGNORE)

    assert "deploy/backups/" in gitignore
    assert "deploy/logs/" in gitignore
    assert "deploy/monitoring/" in gitignore


def test_operations_monitoring_files_do_not_create_cloud_resources() -> None:
    combined = "\n".join(
        read_file(path)
        for path in [
            DISK_SCRIPT,
            STATUS_SCRIPT,
            LOG_SCRIPT,
            MONITOR_SERVICE,
            MONITOR_TIMER,
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
