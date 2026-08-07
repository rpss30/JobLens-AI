from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
UPTIME_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "check_external_uptime.sh"
ALERT_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "send_operations_alert.sh"
WORKFLOW_PATH = ROOT_DIR / ".github" / "workflows" / "uptime-check.yml"
UPTIME_DOC = ROOT_DIR / "docs" / "external-uptime-monitoring.md"
README_PATH = ROOT_DIR / "README.md"
PRODUCTION_DOC = ROOT_DIR / "docs" / "production-deployment.md"
OPERATIONS_DOC = ROOT_DIR / "docs" / "operations-monitoring.md"
GITIGNORE = ROOT_DIR / ".gitignore"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_fake_curl(path: Path, status_code: str) -> None:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                f"printf '{status_code}'",
                "exit 0",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


def test_external_uptime_script_is_executable_and_valid_bash() -> None:
    assert UPTIME_SCRIPT.stat().st_mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(UPTIME_SCRIPT)], check=True)


def test_external_uptime_script_skips_when_unconfigured(tmp_path: Path) -> None:
    status_file = tmp_path / "latest_uptime_check.json"

    result = subprocess.run(
        [str(UPTIME_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "JOBLENS_UPTIME_BASE_URL": "",
            "JOBLENS_DOMAIN": "",
            "UPTIME_STATUS_FILE": str(status_file),
            "SKIP_UPTIME_CHECK_IF_UNCONFIGURED": "true",
        },
        text=True,
    )

    payload = json.loads(status_file.read_text(encoding="utf-8"))

    assert "Skipping external uptime check" in result.stdout
    assert payload["status"] == "skipped"
    assert payload["endpoints"] == []


def test_external_uptime_script_records_successful_endpoint_checks(
    tmp_path: Path,
) -> None:
    status_file = tmp_path / "latest_uptime_check.json"
    fake_curl = tmp_path / "curl"
    write_fake_curl(fake_curl, "200")

    result = subprocess.run(
        [str(UPTIME_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "CURL_BIN": str(fake_curl),
            "JOBLENS_UPTIME_BASE_URL": "https://jobs.test.invalid",
            "UPTIME_PATHS": "/healthz /api/health /ops/login/",
            "UPTIME_STATUS_FILE": str(status_file),
            "UPTIME_DELAY_SECONDS": "1",
        },
        text=True,
    )

    payload = json.loads(status_file.read_text(encoding="utf-8"))

    assert "External uptime check ok" in result.stdout
    assert payload["status"] == "ok"
    assert [endpoint["path"] for endpoint in payload["endpoints"]] == [
        "/healthz",
        "/api/health",
        "/ops/login/",
    ]
    assert {endpoint["status"] for endpoint in payload["endpoints"]} == {"ok"}
    assert {endpoint["status_code"] for endpoint in payload["endpoints"]} == {"200"}


def test_external_uptime_script_records_failure_and_dry_run_alert(
    tmp_path: Path,
) -> None:
    status_file = tmp_path / "latest_uptime_check.json"
    fake_curl = tmp_path / "curl"
    write_fake_curl(fake_curl, "503")

    result = subprocess.run(
        [str(UPTIME_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "CURL_BIN": str(fake_curl),
            "JOBLENS_UPTIME_BASE_URL": "https://jobs.test.invalid",
            "UPTIME_PATHS": "/healthz",
            "UPTIME_STATUS_FILE": str(status_file),
            "UPTIME_RETRIES": "1",
            "ALERT_ON_FAILURE": "true",
            "ALERT_DRY_RUN": "true",
        },
        text=True,
    )

    payload = json.loads(status_file.read_text(encoding="utf-8"))

    assert result.returncode == 1
    assert "dry run: would send external_uptime_failed alert" in result.stdout
    assert payload["status"] == "failed"
    assert payload["endpoints"][0]["status"] == "failed"
    assert payload["endpoints"][0]["status_code"] == "503"


def test_uptime_workflow_is_scheduled_and_uploads_report() -> None:
    workflow = read_file(WORKFLOW_PATH)

    assert "name: External Uptime Check" in workflow
    assert "schedule:" in workflow
    assert "*/30 * * * *" in workflow
    assert "workflow_dispatch:" in workflow
    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "deploy/scripts/check_external_uptime.sh" in workflow
    assert "secrets.PRODUCTION_HEALTH_BASE_URL" in workflow
    assert "secrets.PRODUCTION_DOMAIN" in workflow
    assert "secrets.PRODUCTION_ALERT_WEBHOOK_URL" in workflow
    assert "ALERT_ON_FAILURE=true" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "deploy/uptime-reports/latest_uptime_check.json" in workflow


def test_uptime_reports_are_ignored() -> None:
    gitignore = read_file(GITIGNORE)

    assert "deploy/uptime-reports/" in gitignore

    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "deploy/uptime-reports/latest_uptime_check.json",
        ],
        check=True,
        capture_output=True,
        cwd=ROOT_DIR,
        text=True,
    )

    assert "deploy/uptime-reports/latest_uptime_check.json" in ignored.stdout


def test_uptime_docs_are_linked_and_cover_limits() -> None:
    doc = read_file(UPTIME_DOC).lower()
    readme = read_file(README_PATH)
    production_doc = read_file(PRODUCTION_DOC)
    operations_doc = read_file(OPERATIONS_DOC)

    expected_topics = [
        "external uptime check",
        "/healthz",
        "/api/health",
        "/ops/login/",
        "every 30 minutes",
        "production_health_base_url",
        "production_alert_webhook_url",
        "latest_uptime_check.json",
        "github actions scheduling is not a paging-grade uptime service",
        "no paid external monitoring provider is configured",
    ]

    for topic in expected_topics:
        assert topic in doc

    assert "docs/external-uptime-monitoring.md" in readme
    assert "external-uptime-monitoring.md" in production_doc
    assert "external-uptime-monitoring.md" in operations_doc


def test_uptime_automation_does_not_provision_cloud_resources() -> None:
    combined = "\n".join(
        [
            read_file(UPTIME_SCRIPT),
            read_file(ALERT_SCRIPT),
            read_file(WORKFLOW_PATH),
        ]
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
