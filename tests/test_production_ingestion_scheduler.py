from __future__ import annotations

import os
import stat
import subprocess
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
REFRESH_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "run_ingestion_refresh.sh"
STATUS_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_ingestion_refresh_status.sh"
SYSTEMD_SERVICE = (
    ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-ingestion-refresh.service"
)
SYSTEMD_TIMER = (
    ROOT_DIR / "deploy" / "server" / "systemd" / "joblens-ingestion-refresh.timer"
)
INGESTION_DOC = ROOT_DIR / "docs" / "production-ingestion.md"
README_PATH = ROOT_DIR / "README.md"
PRODUCTION_COMPOSE_DOC = ROOT_DIR / "docs" / "production-compose.md"
PRODUCTION_DEPLOYMENT_DOC = ROOT_DIR / "docs" / "production-deployment.md"
READINESS_DOC = ROOT_DIR / "docs" / "production-readiness.md"
GITIGNORE = ROOT_DIR / ".gitignore"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_ingestion_scheduler_scripts_are_executable_and_valid_bash() -> None:
    for script_path in [REFRESH_SCRIPT, STATUS_SCRIPT]:
        assert script_path.stat().st_mode & stat.S_IXUSR
        subprocess.run(["bash", "-n", str(script_path)], check=True)


def test_ingestion_refresh_script_runs_existing_pipeline_and_seeds_database() -> None:
    script = read_file(REFRESH_SCRIPT)

    expected_steps = [
        "scripts/fetch_canada_jobs.py",
        "scripts/build_canada_jobs_snapshot.py",
        "scripts/validate_canada_jobs_snapshot.py",
        "scripts/seed_database.py",
        "--save-run-to-db",
        "--dataset-name \"${INGESTION_DATASET_NAME}\"",
        "--source-type canada_snapshot",
        "latest_ingestion_refresh.json",
        "canada-fetch-summary.json",
        "canada-snapshot-summary.json",
        "canada-validation-summary.md",
        "compose exec -T \"${INGESTION_SERVICE}\"",
        "compose cp",
    ]

    for expected_step in expected_steps:
        assert expected_step in script

    assert "canada_jobs" in script
    assert "INGESTION_MAX_JOBS" in script
    assert "INGESTION_DELAY_SECONDS" in script
    assert "Compose service is not running" in script
    assert '"status": "%s"' in script
    assert '"stage": "%s"' in script
    assert "write_status \"failed\"" in script
    assert "write_status \"succeeded\"" in script
    assert "docker compose up" not in script


def test_ingestion_status_script_detects_missing_failed_and_stale_statuses(
    tmp_path: Path,
) -> None:
    missing_status = tmp_path / "missing.json"
    missing = subprocess.run(
        [str(STATUS_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "INGESTION_STATUS_FILE": str(missing_status),
            "INGESTION_MAX_AGE_HOURS": "1",
        },
        text=True,
    )

    assert missing.returncode == 1
    assert "Ingestion refresh status file is missing" in missing.stderr

    failed_status = tmp_path / "failed.json"
    failed_status.write_text('{"status": "failed"}\n', encoding="utf-8")
    failed = subprocess.run(
        [str(STATUS_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "INGESTION_STATUS_FILE": str(failed_status),
            "INGESTION_MAX_AGE_HOURS": "1",
        },
        text=True,
    )

    assert failed.returncode == 1
    assert "Latest ingestion refresh did not succeed" in failed.stderr

    stale_status = tmp_path / "stale.json"
    stale_status.write_text('{"status": "succeeded"}\n', encoding="utf-8")
    stale_epoch = time.time() - 7200
    os.utime(stale_status, (stale_epoch, stale_epoch))
    stale = subprocess.run(
        [str(STATUS_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "INGESTION_STATUS_FILE": str(stale_status),
            "INGESTION_MAX_AGE_HOURS": "1",
        },
        text=True,
    )

    assert stale.returncode == 1
    assert "Latest successful ingestion refresh is stale" in stale.stderr

    healthy_status = tmp_path / "healthy.json"
    healthy_status.write_text('{"status": "succeeded"}\n', encoding="utf-8")
    healthy = subprocess.run(
        [str(STATUS_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "INGESTION_STATUS_FILE": str(healthy_status),
            "INGESTION_MAX_AGE_HOURS": "1",
        },
        text=True,
    )

    assert "Latest ingestion refresh is healthy" in healthy.stdout


def test_ingestion_systemd_timer_runs_weekly_with_server_defaults() -> None:
    service = read_file(SYSTEMD_SERVICE)
    timer = read_file(SYSTEMD_TIMER)

    assert "Type=oneshot" in service
    assert "User=joblens" in service
    assert "WorkingDirectory=/srv/joblens-ai" in service
    assert "INGESTION_OUTPUT_DIR=/srv/joblens-ingestion" in service
    assert "INGESTION_STATUS_FILE=/srv/joblens-ingestion/latest_ingestion_refresh.json" in service
    assert "INGESTION_DATASET_NAME=canada_jobs" in service
    assert "INGESTION_MAX_JOBS=72" in service
    assert "INGESTION_DELAY_SECONDS=1" in service
    assert "ExecStart=/srv/joblens-ai/deploy/scripts/run_ingestion_refresh.sh" in service
    assert "OnCalendar=Mon *-*-* 04:30:00" in timer
    assert "Persistent=true" in timer
    assert "RandomizedDelaySec=1800" in timer


def test_ingestion_outputs_are_ignored() -> None:
    gitignore = read_file(GITIGNORE)

    assert "deploy/ingestion/" in gitignore

    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "deploy/ingestion/latest_ingestion_refresh.json"],
        check=True,
        capture_output=True,
        cwd=ROOT_DIR,
        text=True,
    )

    assert "deploy/ingestion/latest_ingestion_refresh.json" in ignored.stdout


def test_ingestion_scheduler_files_do_not_create_cloud_resources() -> None:
    combined = "\n".join(
        read_file(path)
        for path in [
            REFRESH_SCRIPT,
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
        "aws route53 create-hosted-zone",
    ]

    for command in forbidden_commands:
        assert command not in combined


def test_ingestion_scheduler_documentation_is_linked() -> None:
    doc = read_file(INGESTION_DOC).lower()
    readme = read_file(README_PATH)
    compose_doc = read_file(PRODUCTION_COMPOSE_DOC)
    deployment_doc = read_file(PRODUCTION_DEPLOYMENT_DOC)
    readiness_doc = read_file(READINESS_DOC)

    expected_topics = [
        "run_ingestion_refresh.sh",
        "check_ingestion_refresh_status.sh",
        "systemd",
        "weekly refresh",
        "greenhouse, lever, and ashby",
        "groq-enriched canada snapshot",
        "validated snapshot",
        "postgresql `canada_jobs` dataset",
        "latest_ingestion_refresh.json",
        "failure triage",
        "no cloud resources",
        "no route triggers ingestion",
    ]

    for topic in expected_topics:
        assert topic in doc

    assert "docs/production-ingestion.md" in readme
    assert "production-ingestion.md" in compose_doc
    assert "production-ingestion.md" in deployment_doc
    assert "production-ingestion.md" in readiness_doc
