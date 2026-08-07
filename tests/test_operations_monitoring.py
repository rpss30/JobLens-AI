from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DISK_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_disk_usage.sh"
STATUS_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_operations_status.sh"
LOG_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "collect_operations_logs.sh"
LOG_AGGREGATION_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "aggregate_operations_logs.sh"
LOG_AGGREGATION_STATUS_SCRIPT = (
    ROOT_DIR / "deploy" / "scripts" / "check_log_aggregation_status.sh"
)
INGESTION_STATUS_SCRIPT = (
    ROOT_DIR / "deploy" / "scripts" / "check_ingestion_refresh_status.sh"
)
OFFSITE_STATUS_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_offsite_backup_status.sh"
ALERT_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "send_operations_alert.sh"
MONITOR_SERVICE = ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-ops-monitor.service"
MONITOR_TIMER = ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-ops-monitor.timer"
LOG_AGGREGATION_SERVICE = (
    ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-log-aggregation.service"
)
LOG_AGGREGATION_TIMER = (
    ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-log-aggregation.timer"
)
GITIGNORE = ROOT_DIR / ".gitignore"
MONITORING_DOC = ROOT_DIR / "docs" / "operations-monitoring.md"
LOG_AGGREGATION_DOC = ROOT_DIR / "docs" / "log-aggregation.md"
README_PATH = ROOT_DIR / "README.md"
PRODUCTION_COMPOSE_DOC = ROOT_DIR / "docs" / "production-compose.md"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_operations_monitoring_scripts_are_executable_and_valid_bash() -> None:
    for script_path in [
        DISK_SCRIPT,
        STATUS_SCRIPT,
        LOG_SCRIPT,
        LOG_AGGREGATION_SCRIPT,
        LOG_AGGREGATION_STATUS_SCRIPT,
        INGESTION_STATUS_SCRIPT,
        OFFSITE_STATUS_SCRIPT,
        ALERT_SCRIPT,
    ]:
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
            "SKIP_OFFSITE_BACKUP_CHECK": "true",
            "SKIP_INGESTION_REFRESH_CHECK": "true",
            "SKIP_LOG_AGGREGATION_CHECK": "true",
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
        "offsite_backup",
        "ingestion_refresh",
        "log_aggregation",
        "disk_usage",
    ]
    assert {check["status"] for check in payload["checks"]} == {"skipped"}


def test_operations_status_records_alert_delivery_after_failed_check(
    tmp_path: Path,
) -> None:
    status_file = tmp_path / "latest_status.json"

    result = subprocess.run(
        [str(STATUS_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "MONITOR_STATUS_FILE": str(status_file),
            "SKIP_COMPOSE_CHECK": "true",
            "SKIP_PUBLIC_HEALTH_CHECK": "true",
            "SKIP_BACKUP_STATUS_CHECK": "true",
            "SKIP_OFFSITE_BACKUP_CHECK": "false",
            "OFFSITE_BACKUP_STATUS_FILE": str(tmp_path / "missing_offsite.json"),
            "SKIP_INGESTION_REFRESH_CHECK": "true",
            "SKIP_LOG_AGGREGATION_CHECK": "true",
            "SKIP_DISK_CHECK": "true",
            "ALERT_ON_FAILURE": "true",
            "ALERT_DRY_RUN": "true",
        },
        text=True,
    )

    payload = json.loads(status_file.read_text(encoding="utf-8"))
    checks_by_name = {check["name"]: check for check in payload["checks"]}

    assert result.returncode == 1
    assert "dry run: would send operations_status_failed alert" in result.stdout
    assert checks_by_name["offsite_backup"]["status"] == "failed"
    assert checks_by_name["alert_delivery"]["status"] == "ok"


def test_alert_script_dry_run_uses_status_file_without_network(tmp_path: Path) -> None:
    status_file = tmp_path / "latest_status.json"
    status_file.write_text('{"status": "failed"}\n', encoding="utf-8")

    result = subprocess.run(
        [str(ALERT_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "ALERT_STATUS_FILE": str(status_file),
            "ALERT_DRY_RUN": "true",
        },
        text=True,
    )

    assert "dry run: would send operations_status_failed alert" in result.stdout


def test_operations_status_checks_compose_health_backup_and_disk_state() -> None:
    script = read_file(STATUS_SCRIPT)

    assert "EXPECTED_SERVICES" in script
    assert "caddy dashboard api django-ops db" in script
    assert "compose ps --status running --services" in script
    assert "check_production_health.sh" in script
    assert "check_database_backup_status.sh" in script
    assert "check_offsite_backup_status.sh" in script
    assert "check_ingestion_refresh_status.sh" in script
    assert "check_log_aggregation_status.sh" in script
    assert "check_disk_usage.sh" in script
    assert "send_operations_alert.sh" in script
    assert "MONITOR_STATUS_FILE" in script
    assert '"checks": [' in script
    assert "SKIP_PUBLIC_HEALTH_CHECK" in script
    assert "SKIP_OFFSITE_BACKUP_CHECK" in script
    assert "SKIP_INGESTION_REFRESH_CHECK" in script
    assert "SKIP_LOG_AGGREGATION_CHECK" in script
    assert "ALERT_ON_FAILURE" in script


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


def test_log_aggregation_writes_normalized_jsonl_without_real_services(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker_bin = bin_dir / "docker"
    journalctl_bin = bin_dir / "journalctl"
    log_dir = tmp_path / "aggregated"

    docker_bin.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "compose" && "$*" == *" logs "* ]]; then
  service="${@: -1}"
  printf '2026-08-07T12:00:00Z %s ready\\n' "$service"
  exit 0
fi
echo "unexpected docker command: $*" >&2
exit 1
""",
        encoding="utf-8",
    )
    journalctl_bin.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
unit="unknown"
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "-u" ]]; then
    shift
    unit="$1"
  fi
  shift || true
done
printf '2026-08-07T12:01:00+00:00 host %s ok\\n' "$unit"
""",
        encoding="utf-8",
    )
    docker_bin.chmod(0o755)
    journalctl_bin.chmod(0o755)

    result = subprocess.run(
        [str(LOG_AGGREGATION_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "LOG_AGGREGATION_DIR": str(log_dir),
            "LOG_AGGREGATION_RUN_ID": "20260807T120000Z",
            "LOG_AGGREGATION_LINES": "2",
            "LOG_AGGREGATION_RETENTION_DAYS": "7",
            "PYTHON_BIN": sys.executable,
        },
        text=True,
    )

    status = json.loads((log_dir / "latest_log_aggregation.json").read_text())
    records = [
        json.loads(line)
        for line in (log_dir / "20260807T120000Z.jsonl").read_text().splitlines()
    ]

    assert "Operations log aggregation succeeded" in result.stdout
    assert status["status"] == "succeeded"
    assert status["line_count"] == 8
    assert status["retention_days"] == 7
    assert {record["source"] for record in records} == {"compose", "systemd"}
    assert {"caddy", "dashboard", "api", "django-ops", "db"} <= {
        record["name"] for record in records
    }
    assert "joblens-ingestion-refresh.service" in {
        record["name"] for record in records
    }


def test_log_aggregation_status_requires_successful_fresh_run(tmp_path: Path) -> None:
    status_file = tmp_path / "latest_log_aggregation.json"
    status_file.write_text('{"status": "succeeded"}\n', encoding="utf-8")

    healthy = subprocess.run(
        [str(LOG_AGGREGATION_STATUS_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "LOG_AGGREGATION_STATUS_FILE": str(status_file),
            "LOG_AGGREGATION_MAX_AGE_HOURS": "6",
        },
        text=True,
    )

    status_file.write_text('{"status": "failed"}\n', encoding="utf-8")
    failed = subprocess.run(
        [str(LOG_AGGREGATION_STATUS_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "LOG_AGGREGATION_STATUS_FILE": str(status_file),
            "LOG_AGGREGATION_MAX_AGE_HOURS": "6",
        },
        text=True,
    )

    assert "Latest log aggregation is healthy" in healthy.stdout
    assert failed.returncode == 1
    assert "Latest log aggregation did not succeed" in failed.stderr


def test_monitoring_timer_runs_every_five_minutes_with_server_defaults() -> None:
    service = read_file(MONITOR_SERVICE)
    timer = read_file(MONITOR_TIMER)

    assert "Type=oneshot" in service
    assert "User=joblens" in service
    assert "WorkingDirectory=/srv/joblens-ai" in service
    assert "BACKUP_STATUS_FILE=/srv/joblens-backups/latest_backup.json" in service
    assert "BACKUP_MAX_AGE_HOURS=30" in service
    assert (
        "OFFSITE_BACKUP_STATUS_FILE=/srv/joblens-backups/latest_offsite_backup.json"
        in service
    )
    assert "OFFSITE_BACKUP_MAX_AGE_HOURS=30" in service
    assert "INGESTION_STATUS_FILE=/srv/joblens-ingestion/latest_ingestion_refresh.json" in service
    assert "INGESTION_MAX_AGE_HOURS=192" in service
    assert "LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json" in service
    assert "LOG_AGGREGATION_MAX_AGE_HOURS=6" in service
    assert "DISK_PATHS=/ /srv/joblens-backups /srv/joblens-logs" in service
    assert "DISK_WARN_PERCENT=80" in service
    assert "DISK_CRITICAL_PERCENT=90" in service
    assert "SKIP_PUBLIC_HEALTH_CHECK=true" in service
    assert "SKIP_OFFSITE_BACKUP_CHECK=true" in service
    assert "SKIP_LOG_AGGREGATION_CHECK=false" in service
    assert "ALERT_ON_FAILURE=false" in service
    assert "MONITOR_STATUS_FILE=/srv/joblens-monitoring/latest_status.json" in service
    assert "ExecStart=/srv/joblens-ai/deploy/scripts/check_operations_status.sh" in service
    assert "OnCalendar=*:0/5" in timer
    assert "Persistent=true" in timer
    assert "RandomizedDelaySec=30" in timer


def test_log_aggregation_timer_runs_every_fifteen_minutes_with_server_defaults() -> None:
    service = read_file(LOG_AGGREGATION_SERVICE)
    timer = read_file(LOG_AGGREGATION_TIMER)

    assert "Type=oneshot" in service
    assert "User=joblens" in service
    assert "WorkingDirectory=/srv/joblens-ai" in service
    assert "LOG_AGGREGATION_DIR=/srv/joblens-logs" in service
    assert "LOG_AGGREGATION_STATUS_FILE=/srv/joblens-logs/latest_log_aggregation.json" in service
    assert "LOG_AGGREGATION_SERVICES=caddy dashboard api django-ops db" in service
    assert "LOG_AGGREGATION_LINES=400" in service
    assert "LOG_AGGREGATION_RETENTION_DAYS=14" in service
    assert "INCLUDE_SYSTEMD_LOGS=true" in service
    assert "ExecStart=/srv/joblens-ai/deploy/scripts/aggregate_operations_logs.sh" in service
    assert "OnCalendar=*:0/15" in timer
    assert "Persistent=true" in timer
    assert "RandomizedDelaySec=60" in timer


def test_generated_operations_outputs_are_ignored() -> None:
    gitignore = read_file(GITIGNORE)

    assert "deploy/backups/" in gitignore
    assert "deploy/log-aggregation/" in gitignore
    assert "deploy/logs/" in gitignore
    assert "deploy/monitoring/" in gitignore


def test_operations_monitoring_files_do_not_create_cloud_resources() -> None:
    combined = "\n".join(
        read_file(path)
        for path in [
            DISK_SCRIPT,
            STATUS_SCRIPT,
            LOG_SCRIPT,
            LOG_AGGREGATION_SCRIPT,
            LOG_AGGREGATION_STATUS_SCRIPT,
            INGESTION_STATUS_SCRIPT,
            OFFSITE_STATUS_SCRIPT,
            ALERT_SCRIPT,
            MONITOR_SERVICE,
            MONITOR_TIMER,
            LOG_AGGREGATION_SERVICE,
            LOG_AGGREGATION_TIMER,
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


def test_operations_monitoring_documentation_covers_checks_and_limits() -> None:
    doc = read_file(MONITORING_DOC).lower()
    log_doc = read_file(LOG_AGGREGATION_DOC).lower()
    readme = read_file(README_PATH)
    compose_doc = read_file(PRODUCTION_COMPOSE_DOC)

    expected_topics = [
        "compose services",
        "public health",
        "database backup",
        "off-server backup",
        "latest_offsite_backup.json",
        "ingestion refresh",
        "latest_ingestion_refresh.json",
        "disk usage",
        "latest_status.json",
        "check_operations_status.sh",
        "check_disk_usage.sh",
        "collect_operations_logs.sh",
        "check_offsite_backup_status.sh",
        "check_ingestion_refresh_status.sh",
        "aggregate_operations_logs.sh",
        "check_log_aggregation_status.sh",
        "latest_log_aggregation.json",
        "central log aggregation",
        "send_operations_alert.sh",
        "systemd",
        "failure triage",
        "no cloud resources",
        "external uptime monitoring runs through github actions",
        "generic webhook",
        "not a paging escalation policy",
    ]

    for topic in expected_topics:
        assert topic in doc

    for topic in [
        "normalized jsonl",
        "server-local",
        "retention",
        "joblens-log-aggregation.timer",
        "no cloud resources",
    ]:
        assert topic in log_doc

    assert "docs/operations-monitoring.md" in readme
    assert "docs/log-aggregation.md" in readme
    assert "operations-monitoring.md" in compose_doc
    assert "log-aggregation.md" in compose_doc
