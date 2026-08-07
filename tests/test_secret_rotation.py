from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = ROOT_DIR / "deploy" / "scripts" / "audit_secret_configuration.sh"
PARAMETER_RENDER_SCRIPT = (
    ROOT_DIR / "deploy" / "scripts" / "render_env_from_parameter_store.sh"
)
GITIGNORE = ROOT_DIR / ".gitignore"
SECRET_ROTATION_DOC = ROOT_DIR / "docs" / "secret-rotation.md"
PARAMETER_STORE_DOC = ROOT_DIR / "docs" / "parameter-store-secrets.md"
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
    for script_path in [AUDIT_SCRIPT, PARAMETER_RENDER_SCRIPT]:
        assert script_path.stat().st_mode & stat.S_IXUSR
        subprocess.run(["bash", "-n", str(script_path)], check=True)


def write_fake_aws_cli(path: Path, response_path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "printf '%s\\n' \"$*\" > \"$FAKE_AWS_ARGS_FILE\"",
                f"cat {response_path}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


def write_parameter_response(path: Path, *, include_database_url: bool = True) -> None:
    parameters = [
        {
            "Name": "/joblens/production/POSTGRES_PASSWORD",
            "Value": "prod-postgres-password-value",
        },
        {
            "Name": "/joblens/production/JOBLENS_DOMAIN",
            "Value": "jobs.test.invalid",
        },
        {
            "Name": "/joblens/production/CADDY_ACME_EMAIL",
            "Value": "admin@test.invalid",
        },
        {
            "Name": "/joblens/production/JOBLENS_CORS_ORIGINS",
            "Value": "https://jobs.test.invalid",
        },
        {
            "Name": "/joblens/production/DJANGO_SECRET_KEY",
            "Value": "prod-django-secret-key-value",
        },
        {
            "Name": "/joblens/production/DJANGO_ALLOWED_HOSTS",
            "Value": "jobs.test.invalid",
        },
        {
            "Name": "/joblens/production/DJANGO_CSRF_TRUSTED_ORIGINS",
            "Value": "https://jobs.test.invalid",
        },
        {
            "Name": "/joblens/production/GROQ_API_KEY",
            "Value": "prod-groq-key-value",
        },
    ]

    if include_database_url:
        parameters.append(
            {
                "Name": "/joblens/production/DATABASE_URL",
                "Value": (
                    "postgresql+psycopg://joblens:"
                    "prod-postgres-password-value@db:5432/joblens_ai"
                ),
            }
        )

    path.write_text(json.dumps({"Parameters": parameters}), encoding="utf-8")


def test_parameter_store_renderer_writes_private_env_and_audits(
    tmp_path: Path,
) -> None:
    response_path = tmp_path / "parameters.json"
    fake_aws_path = tmp_path / "aws"
    args_file = tmp_path / "aws-args.txt"
    env_file = tmp_path / ".env.production"
    status_file = tmp_path / "parameter-store-status.json"
    audit_status_file = tmp_path / "secret-audit.json"
    write_parameter_response(response_path)
    write_fake_aws_cli(fake_aws_path, response_path)

    result = subprocess.run(
        [str(PARAMETER_RENDER_SCRIPT)],
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "AWS_CLI": str(fake_aws_path),
            "FAKE_AWS_ARGS_FILE": str(args_file),
            "PARAMETER_STORE_PATH": "/joblens/production",
            "ENV_FILE": str(env_file),
            "PARAMETER_STORE_STATUS_FILE": str(status_file),
            "PARAMETER_STORE_AUDIT_STATUS_FILE": str(audit_status_file),
            "RUN_SECRET_AUDIT": "true",
        },
        cwd=ROOT_DIR,
        text=True,
    )

    rendered_env = env_file.read_text(encoding="utf-8")
    status_payload = json.loads(status_file.read_text(encoding="utf-8"))
    audit_payload = json.loads(audit_status_file.read_text(encoding="utf-8"))
    combined_output = (
        result.stdout
        + result.stderr
        + status_file.read_text(encoding="utf-8")
        + audit_status_file.read_text(encoding="utf-8")
    )

    assert "ssm get-parameters-by-path" in args_file.read_text(encoding="utf-8")
    assert "--with-decryption" in args_file.read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD=prod-postgres-password-value" in rendered_env
    assert "DJANGO_SECRET_KEY=prod-django-secret-key-value" in rendered_env
    assert "GEMINI_API_KEY=" in rendered_env
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert status_payload["status"] == "succeeded"
    assert "POSTGRES_PASSWORD" in status_payload["rendered_keys"]
    assert "GEMINI_API_KEY" in status_payload["blank_keys"]
    assert audit_payload["status"] == "succeeded"
    assert "no secret values were printed" in result.stdout
    assert "prod-postgres-password-value" not in combined_output
    assert "prod-django-secret-key-value" not in combined_output


def test_parameter_store_renderer_dry_run_detects_missing_required_key(
    tmp_path: Path,
) -> None:
    response_path = tmp_path / "parameters.json"
    fake_aws_path = tmp_path / "aws"
    args_file = tmp_path / "aws-args.txt"
    env_file = tmp_path / ".env.production"
    status_file = tmp_path / "parameter-store-status.json"
    write_parameter_response(response_path, include_database_url=False)
    write_fake_aws_cli(fake_aws_path, response_path)

    result = subprocess.run(
        [str(PARAMETER_RENDER_SCRIPT)],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "AWS_CLI": str(fake_aws_path),
            "FAKE_AWS_ARGS_FILE": str(args_file),
            "PARAMETER_STORE_PATH": "/joblens/production",
            "PARAMETER_STORE_DRY_RUN": "true",
            "ENV_FILE": str(env_file),
            "PARAMETER_STORE_STATUS_FILE": str(status_file),
            "RUN_SECRET_AUDIT": "false",
        },
        cwd=ROOT_DIR,
        text=True,
    )

    status_payload = json.loads(status_file.read_text(encoding="utf-8"))

    assert result.returncode == 1
    assert not env_file.exists()
    assert status_payload["status"] == "failed"
    assert status_payload["dry_run"] is True
    assert status_payload["missing_keys"] == ["DATABASE_URL"]


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
    combined = "\n".join(
        [
            AUDIT_SCRIPT.read_text(encoding="utf-8"),
            PARAMETER_RENDER_SCRIPT.read_text(encoding="utf-8"),
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

    for forbidden_write in [
        "ssm put-parameter",
        "ssm delete-parameter",
        "ssm label-parameter-version",
        "kms create-key",
        "iam create-role",
    ]:
        assert forbidden_write not in combined

    assert "get-parameters-by-path" in combined


def test_secret_rotation_documentation_covers_inventory_rotation_and_emergency_steps() -> None:
    doc = SECRET_ROTATION_DOC.read_text(encoding="utf-8").lower()
    parameter_doc = PARAMETER_STORE_DOC.read_text(encoding="utf-8").lower()
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
        "parameter store",
        "explicit approval before any paid resource is created",
    ]

    for topic in expected_topics:
        assert topic in doc

    for topic in [
        "getparametersbypath",
        "get-parameters-by-path",
        "with-decryption",
        "0600",
        "key-name only",
        "no parameters, iam policies, kms keys, or cloud resources are created",
        "ssm:getparametersbypath",
        "no automatic provider-side key rotation",
    ]:
        assert topic in parameter_doc

    assert "docs/secret-rotation.md" in readme
    assert "docs/parameter-store-secrets.md" in readme
    assert "secret-rotation.md" in security_doc
    assert "parameter-store-secrets.md" in security_doc
    assert "secret-rotation.md" in deployment_doc
    assert "parameter-store-secrets.md" in deployment_doc
