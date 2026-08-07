from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
LIGHTSAIL_DIR = ROOT_DIR / "deploy" / "lightsail"
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


def test_lightsail_folder_contains_no_provisioning_automation() -> None:
    disallowed_suffixes = {".sh", ".tf", ".tfvars", ".yml", ".yaml"}
    files = [path for path in LIGHTSAIL_DIR.rglob("*") if path.is_file()]

    assert files

    for path in files:
        assert path.suffix not in disallowed_suffixes

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


def test_lightsail_plan_is_linked_from_project_docs() -> None:
    readme = read_text(README)
    readiness_doc = read_text(READINESS_DOC)

    assert "docs/lightsail-deployment-plan.md" in readme
    assert "Lightsail deployment plan" in readme
    assert "lightsail-deployment-plan.md" in readiness_doc
    assert "deploy/lightsail/resource-plan.example.json" in readiness_doc
