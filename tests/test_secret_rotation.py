from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "audit_secret_configuration.sh"
GITIGNORE = ROOT_DIR / ".gitignore"
SECRET_ROTATION_DOC = ROOT_DIR / "docs" / "secret-rotation.md"
README_PATH = ROOT_DIR / "README.md"
SECURITY_DOC = ROOT_DIR / "docs" / "security.md"
PRODUCTION_DEPLOYMENT_DOC = ROOT_DIR / "docs" / "production-deployment.md"


def write_fake_production_env(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "POSTGRES_PASSWORD=prod-postgres-password-value",
                "DATABASE_URL=postgresql+psycopg://joblens:prod-postgres-password-value@db:5432/joblens_ai",
                "JOBLENS_DOMAIN=jobs.test.invalid",
                "CADDY_ACME_EMAIL=admin@test.invalid",
                "JOBLENS_CORS_ORIGINS=https://jobs.test.invalid",
                "DJANGO_SECRET_KEY=prod-django-secret-key-value",
                "DJANGO_ALLOWED_HOSTS=jobs.test.invalid",
                "DJANGO_CSRF_TRUSTED_ORIGINS=https://jobs.test.invalid",
                "GROQ_API_KEY=",
                "GEMINI_API_KEY=",
            ],
        )
        + "\n",
        encoding="utf-8",
    )


def test_secret_audit_script_is_executable_and_valid_bash() -> None:
    assert AUDIT_SCRIPT.stat().st_mode & stat.S_IXUSR
    subprocess.run(["bash", "-n", str(AUDIT_SCRIPT)], check=True)


def test_secret_audit_passes_valid_env_without_printing_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.production"
    status_file = tmp_path / "secret-audit.json"
    write_fake_production_env(env_file)
    env_file.chmod(0o600)

    result = subprocess.run(
        [str(AUDIT_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "ENV_FILE": str(env_file),
            "AUDIT_STATUS_FILE": str(status_file),
        },
        text=True,
    )

    payload = json.loads(status_file.read_text(encoding="utf-8"))
    combined_output = result.stdout + result.stderr + status_file.read_text(encoding="utf-8")

    assert payload["status"] == "succeeded"
    assert payload["failures"] == []
    assert "GROQ_API_KEY is not configured" in payload["warnings"]
    assert "GEMINI_API_KEY is not configured" in payload["warnings"]
    assert "no secret values were printed" in result.stdout
    assert "prod-postgres-password-value" not in combined_output
    assert "prod-django-secret-key-value" not in combined_output


def test_secret_audit_fails_placeholder_missing_and_public_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.production"
    status_file = tmp_path / "secret-audit.json"
    env_file.write_text("POSTGRES_PASSWORD=replace-with-a-long-random-password\n", encoding="utf-8")
    env_file.chmod(0o644)

    result = subprocess.run(
        [str(AUDIT_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "ENV_FILE": str(env_file),
            "AUDIT_STATUS_FILE": str(status_file),
        },
        text=True,
    )

    payload = json.loads(status_file.read_text(encoding="utf-8"))

    assert result.returncode == 1
    assert payload["status"] == "failed"
    assert "env file permissions allow group or other access" in payload["failures"]
    assert "POSTGRES_PASSWORD is empty or still uses a placeholder value" in payload["failures"]
    assert "DATABASE_URL is missing" in payload["failures"]
    assert "Secret configuration audit failed" in result.stderr
    assert "replace-with-a-long-random-password" not in result.stdout + result.stderr


def test_production_env_files_are_ignored_but_examples_are_allowed() -> None:
    gitignore = GITIGNORE.read_text(encoding="utf-8")

    assert ".env.*" in gitignore
    assert "!.env.example" in gitignore
    assert "!.env.production.example" in gitignore
    assert "deploy/secret-audits/" in gitignore

    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", ".env.production"],
        check=True,
        capture_output=True,
        cwd=ROOT_DIR,
        text=True,
    )
    example = subprocess.run(
        ["git", "check-ignore", "--no-index", ".env.production.example"],
        check=False,
        capture_output=True,
        cwd=ROOT_DIR,
        text=True,
    )

    assert ".env.production" in ignored.stdout
    assert example.returncode == 1


def test_secret_audit_script_does_not_provision_cloud_resources() -> None:
    script = AUDIT_SCRIPT.read_text(encoding="utf-8").lower()

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
        assert command not in script


def test_secret_rotation_documentation_covers_inventory_rotation_and_emergency_steps() -> None:
    doc = SECRET_ROTATION_DOC.read_text(encoding="utf-8").lower()
    readme = README_PATH.read_text(encoding="utf-8")
    security_doc = SECURITY_DOC.read_text(encoding="utf-8")
    deployment_doc = PRODUCTION_DEPLOYMENT_DOC.read_text(encoding="utf-8")

    expected_topics = [
        "postgres_password",
        "database_url",
        "django_secret_key",
        "groq_api_key",
        "gemini_api_key",
        "production_ssh_key",
        "audit_secret_configuration.sh",
        "no secret values",
        "postgresql password rotation",
        "django secret key rotation",
        "provider api key rotation",
        "deployment ssh key rotation",
        "emergency replacement",
        "no secret manager integration",
        "explicit approval before any paid resource is created",
    ]

    for topic in expected_topics:
        assert topic in doc

    assert "docs/secret-rotation.md" in readme
    assert "secret-rotation.md" in security_doc
    assert "secret-rotation.md" in deployment_doc
