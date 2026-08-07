from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SCAN_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "run_security_scans.sh"
WORKFLOW_PATH = ROOT_DIR / ".github" / "workflows" / "security-scan.yml"
SECURITY_DOC = ROOT_DIR / "docs" / "security-scanning.md"
README_PATH = ROOT_DIR / "README.md"
TESTING_DOC = ROOT_DIR / "docs" / "testing.md"
PRODUCTION_DOC = ROOT_DIR / "docs" / "production-deployment.md"
SECURITY_OVERVIEW_DOC = ROOT_DIR / "docs" / "security.md"
GITIGNORE = ROOT_DIR / ".gitignore"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_fake_scanner(path: Path, marker: str) -> None:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "output_path=\"\"",
                "while [[ $# -gt 0 ]]; do",
                "  if [[ \"$1\" == \"--output\" || \"$1\" == \"-o\" ]]; then",
                "    output_path=\"$2\"",
                "    shift 2",
                "    continue",
                "  fi",
                "  shift",
                "done",
                "if [[ -n \"${output_path}\" ]]; then",
                "  mkdir -p \"$(dirname \"${output_path}\")\"",
                f"  printf '{{\"scanner\":\"{marker}\"}}\\n' > \"${{output_path}}\"",
                "fi",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


def test_security_scan_script_is_executable_and_valid_bash() -> None:
    assert SCAN_SCRIPT.stat().st_mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(SCAN_SCRIPT)], check=True)


def test_security_scan_script_runs_fake_dependency_and_static_scans(
    tmp_path: Path,
) -> None:
    report_dir = tmp_path / "reports"
    status_file = report_dir / "latest_security_scan.json"
    fake_pip_audit = tmp_path / "pip-audit"
    fake_bandit = tmp_path / "bandit"
    write_fake_scanner(fake_pip_audit, "pip-audit")
    write_fake_scanner(fake_bandit, "bandit")

    result = subprocess.run(
        [str(SCAN_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "SECURITY_SCAN_REPORT_DIR": str(report_dir),
            "SECURITY_SCAN_STATUS_FILE": str(status_file),
            "PIP_AUDIT_BIN": str(fake_pip_audit),
            "BANDIT_BIN": str(fake_bandit),
            "RUN_TRIVY_IMAGE_SCAN": "false",
        },
        cwd=ROOT_DIR,
        text=True,
    )

    status_payload = json.loads(status_file.read_text(encoding="utf-8"))
    checks_by_name = {check["name"]: check for check in status_payload["checks"]}

    assert "Security scans passed" in result.stdout
    assert json.loads((report_dir / "pip-audit.json").read_text())["scanner"] == "pip-audit"
    assert json.loads((report_dir / "bandit.json").read_text())["scanner"] == "bandit"
    assert status_payload["status"] == "passed"
    assert checks_by_name["pip_audit"]["status"] == "ok"
    assert checks_by_name["bandit"]["status"] == "ok"
    assert checks_by_name["trivy_image"]["status"] == "skipped"


def test_security_scan_script_records_failed_scanner(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    status_file = report_dir / "latest_security_scan.json"
    fake_bandit = tmp_path / "bandit"
    fake_bandit.write_text("#!/usr/bin/env bash\nexit 7\n", encoding="utf-8")
    fake_bandit.chmod(0o700)

    result = subprocess.run(
        [str(SCAN_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "SECURITY_SCAN_REPORT_DIR": str(report_dir),
            "SECURITY_SCAN_STATUS_FILE": str(status_file),
            "RUN_PIP_AUDIT": "false",
            "BANDIT_BIN": str(fake_bandit),
            "RUN_TRIVY_IMAGE_SCAN": "false",
        },
        cwd=ROOT_DIR,
        text=True,
    )

    status_payload = json.loads(status_file.read_text(encoding="utf-8"))
    checks_by_name = {check["name"]: check for check in status_payload["checks"]}

    assert result.returncode == 1
    assert "Security scans failed" in result.stdout
    assert checks_by_name["pip_audit"]["status"] == "skipped"
    assert checks_by_name["bandit"]["status"] == "failed"
    assert checks_by_name["bandit"]["exit_code"] == 7


def test_security_scan_script_supports_trivy_image_scan() -> None:
    script = read_file(SCAN_SCRIPT)

    assert "RUN_TRIVY_IMAGE_SCAN" in script
    assert "BUILD_IMAGE_BEFORE_TRIVY" in script
    assert "docker build -t" in script
    assert "trivy-image.json" in script
    assert "--severity \"${TRIVY_SEVERITY}\"" in script
    assert "--ignore-unfixed" in script
    assert "HIGH,CRITICAL" in script


def test_security_scan_workflow_runs_python_and_container_jobs() -> None:
    workflow = read_file(WORKFLOW_PATH)

    assert "name: Security Scan" in workflow
    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "permissions:" in workflow
    assert "contents: read" in workflow
    assert "python-security:" in workflow
    assert "container-security:" in workflow
    assert "python -m pip install pip-audit bandit" in workflow
    assert "deploy/scripts/run_security_scans.sh" in workflow
    assert "RUN_TRIVY_IMAGE_SCAN=false" in workflow
    assert "docker build -t joblens-security-scan:${{ github.sha }} ." in workflow
    assert "aquasec/trivy:latest" in workflow
    assert "--severity HIGH,CRITICAL" in workflow
    assert "actions/upload-artifact@v4" in workflow


def test_security_reports_are_ignored() -> None:
    gitignore = read_file(GITIGNORE)

    assert "deploy/security-reports/" in gitignore

    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "--no-index",
            "deploy/security-reports/latest_security_scan.json",
        ],
        check=True,
        capture_output=True,
        cwd=ROOT_DIR,
        text=True,
    )

    assert "deploy/security-reports/latest_security_scan.json" in ignored.stdout


def test_security_scan_docs_are_linked_and_cover_limits() -> None:
    doc = read_file(SECURITY_DOC).lower()
    readme = read_file(README_PATH)
    testing_doc = read_file(TESTING_DOC).lower()
    production_doc = read_file(PRODUCTION_DOC)
    security_overview = read_file(SECURITY_OVERVIEW_DOC)

    expected_topics = [
        "pip-audit",
        "bandit",
        "trivy",
        "deploy/security-reports",
        "latest_security_scan.json",
        "dependency finding",
        "static finding",
        "container finding",
        "no image is pushed to a registry",
        "no runtime penetration testing",
    ]

    for topic in expected_topics:
        assert topic in doc

    assert "docs/security-scanning.md" in readme
    assert "security scan workflow" in testing_doc
    assert "security-scanning.md" in production_doc
    assert "security-scanning.md" in security_overview


def test_security_scanning_automation_does_not_provision_cloud_resources() -> None:
    combined = "\n".join([read_file(SCAN_SCRIPT), read_file(WORKFLOW_PATH)]).lower()

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
