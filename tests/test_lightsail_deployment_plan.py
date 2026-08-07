from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
LIGHTSAIL_DIR = ROOT_DIR / "deploy" / "lightsail"
TERRAFORM_DIR = LIGHTSAIL_DIR / "terraform"
LIGHTSAIL_DOC = ROOT_DIR / "docs" / "lightsail-deployment-plan.md"
RESOURCE_PLAN = LIGHTSAIL_DIR / "resource-plan.example.json"
README = ROOT_DIR / "README.md"
READINESS_DOC = ROOT_DIR / "docs" / "production-readiness.md"
GITIGNORE = ROOT_DIR / ".gitignore"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lightsail_deployment_plan_covers_costs_approval_and_teardown() -> None:
    doc = read_text(LIGHTSAIL_DOC).lower()

    expected_topics = [
        "plan-only",
        "creates no cloud resources",
        "explicit approval",
        "aws budget",
        "billing alert",
        "$12",
        "$24",
        "static ipv4",
        "$0.005/hour",
        "$0.05/gb-month",
        "teardown checklist",
        "delete the static ipv4 address",
        "no lightsail resources are provisioned",
        "deploy/lightsail/terraform",
        "init -backend=false",
        "terraform plan",
        "https://aws.amazon.com/lightsail/pricing/",
        "amazon-lightsail-bundles.html",
        "amazon-lightsail-frequently-asked-questions",
    ]

    for topic in expected_topics:
        assert topic in doc


def test_lightsail_resource_plan_is_commit_safe_template() -> None:
    payload = json.loads(read_text(RESOURCE_PLAN))

    assert payload["status"] == "plan_only"
    assert payload["approval_required_before_create"] is True
    assert payload["terraform_template_path"] == "deploy/lightsail/terraform"
    assert payload["estimated_monthly_usd"]["baseline"] == 12
    assert payload["estimated_monthly_usd"]["fallback_4gb_instance"] == 24

    resources = {resource["id"]: resource for resource in payload["resources"]}

    for expected_id in [
        "lightsail-instance",
        "static-ipv4",
        "dns-record",
        "local-docker-volumes",
        "snapshot",
    ]:
        assert expected_id in resources

    assert resources["lightsail-instance"]["status"] == "not_created"
    assert resources["static-ipv4"]["monthly_usd_when_attached"] == 0
    assert resources["static-ipv4"]["unattached_rate_usd_per_hour"] == 0.005
    assert resources["snapshot"]["monthly_usd_per_gb"] == 0.05

    for resource in resources.values():
        assert resource["status"] not in {"active", "created", "provisioned"}


def test_lightsail_folder_contains_only_review_artifacts_and_terraform_template() -> None:
    allowed_suffixes = {".json", ".md", ".tf", ".example", ".hcl"}
    files = [
        path
        for path in LIGHTSAIL_DIR.rglob("*")
        if path.is_file() and ".terraform" not in path.parts
    ]

    assert files

    for path in files:
        assert path.suffix in allowed_suffixes

    plan_text = read_text(RESOURCE_PLAN).lower()

    for command in [
        "aws lightsail create-instances",
        "aws lightsail allocate-static-ip",
        "aws lightsail attach-static-ip",
        "terraform apply",
    ]:
        assert command not in plan_text


def test_lightsail_private_inventory_outputs_are_ignored() -> None:
    gitignore = read_text(GITIGNORE)

    assert "deploy/lightsail/production-inventory.json" in gitignore
    assert "deploy/lightsail/deployment-evidence/" in gitignore
    assert "deploy/lightsail/terraform/.terraform/" in gitignore
    assert "deploy/lightsail/terraform/*.tfplan" in gitignore
    assert "deploy/lightsail/terraform/*.tfstate" in gitignore
    assert "deploy/lightsail/terraform/terraform.tfvars" in gitignore


def test_lightsail_plan_is_linked_from_project_docs() -> None:
    readme = read_text(README)
    readiness_doc = read_text(READINESS_DOC)

    assert "docs/lightsail-deployment-plan.md" in readme
    assert "Lightsail deployment plan" in readme
    assert "Terraform scaffold" in readme
    assert "lightsail-deployment-plan.md" in readiness_doc
    assert "deploy/lightsail/resource-plan.example.json" in readiness_doc


def test_lightsail_terraform_template_defines_bounded_resources() -> None:
    main_tf = read_text(TERRAFORM_DIR / "main.tf")
    variables_tf = read_text(TERRAFORM_DIR / "variables.tf")
    outputs_tf = read_text(TERRAFORM_DIR / "outputs.tf")
    versions_tf = read_text(TERRAFORM_DIR / "versions.tf")
    example_vars = read_text(TERRAFORM_DIR / "terraform.tfvars.example")
    readme = read_text(TERRAFORM_DIR / "README.md").lower()

    expected_resources = [
        'resource "aws_lightsail_instance" "app"',
        'resource "aws_lightsail_static_ip" "app"',
        'resource "aws_lightsail_static_ip_attachment" "app"',
        'resource "aws_lightsail_instance_public_ports" "app"',
    ]

    for resource in expected_resources:
        assert resource in main_tf

    forbidden_resources = [
        "aws_db_instance",
        "aws_lightsail_database",
        "aws_lb",
        "aws_elb",
        "aws_s3_bucket",
        "aws_nat_gateway",
        "aws_ecs_service",
        "aws_route53_zone",
    ]

    combined = "\n".join([main_tf, variables_tf, outputs_tf, versions_tf]).lower()

    for resource in forbidden_resources:
        assert resource not in combined

    assert 'source  = "hashicorp/aws"' in versions_tf
    assert 'version = "~> 6.0"' in versions_tf
    assert "default_tags" in main_tf
    assert "merge(\n    var.extra_tags," in main_tf
    assert "Project     = \"JobLens\"" in main_tf
    assert "ManagedBy   = \"Terraform\"" in main_tf
    assert "ip_address_type   = \"ipv4\"" in main_tf
    assert "from_port  = 80" in main_tf
    assert "from_port  = 443" in main_tf
    assert "from_port  = 22" in main_tf
    assert "0.0.0.0/0" in main_tf
    assert "cidr != \"0.0.0.0/0\"" in variables_tf
    assert "203.0.113.10/32" in example_vars
    assert "terraform apply" in readme

    for internal_port in ["5432", "8000", "8001", "8501"]:
        assert internal_port not in main_tf


def test_lightsail_terraform_readme_documents_validation_and_approval() -> None:
    readme = read_text(TERRAFORM_DIR / "README.md").lower()

    expected_topics = [
        "terraform fmt -check",
        "init -backend=false",
        "terraform validate",
        "approval gate",
        "do not apply",
        "aws lightsail get-blueprints",
        "aws lightsail get-bundles",
        "ssh is limited",
        "postgresql, fastapi, django operations, and streamlit ports stay private",
    ]

    for topic in expected_topics:
        assert topic in readme


def test_lightsail_terraform_validates_when_cli_is_available() -> None:
    if shutil.which("terraform") is None:
        pytest.skip("terraform is not installed")

    subprocess.run(
        ["terraform", f"-chdir={TERRAFORM_DIR}", "fmt", "-check", "-recursive"],
        check=True,
        cwd=ROOT_DIR,
    )
    subprocess.run(
        ["terraform", f"-chdir={TERRAFORM_DIR}", "init", "-backend=false", "-input=false"],
        check=True,
        cwd=ROOT_DIR,
    )
    subprocess.run(
        ["terraform", f"-chdir={TERRAFORM_DIR}", "validate"],
        check=True,
        cwd=ROOT_DIR,
    )
