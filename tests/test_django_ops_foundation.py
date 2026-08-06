from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from django_ops.config.settings import database_config_from_url
from django_ops.pipeline.auth import OPS_VIEWER_GROUP
from django_ops.pipeline import services
from django_ops.pipeline.models import (
    Dataset,
    ExtractionResult,
    IngestionRun,
    JobPosting,
    ProcessedJob,
)


pytestmark = pytest.mark.django_db


@pytest.fixture()
def pipeline_tables(transactional_db):
    models = [
        Dataset,
        JobPosting,
        ProcessedJob,
        IngestionRun,
        ExtractionResult,
    ]

    with connection.schema_editor() as schema_editor:
        for model in models:
            schema_editor.create_model(model)

    yield

    with connection.schema_editor() as schema_editor:
        for model in reversed(models):
            schema_editor.delete_model(model)


@pytest.fixture()
def seeded_pipeline_data(pipeline_tables):
    now = timezone.now()
    dataset = Dataset.objects.create(
        name="canada_jobs",
        source_type="canada_snapshot",
        created_at=now,
    )
    run = IngestionRun.objects.create(
        dataset=dataset,
        source_type="canada_jobs_fetch",
        status="partial_success",
        started_at=now,
        completed_at=now,
        total_sources=3,
        successful_sources=2,
        failed_sources=1,
        raw_job_count=42,
        processed_job_count=40,
        error_log=["Example source failed"],
        run_metadata={"dedup_rejected_count": 2},
    )
    posting = JobPosting.objects.create(
        dataset=dataset,
        job_id="job-1",
        title="Data Engineer",
        company="Example",
        location="Toronto, ON",
        description="Build Python pipelines.",
        experience_level="Mid Level",
        source="greenhouse",
        source_url="https://example.com/jobs/1",
        is_remote=False,
        created_at=now,
    )
    processed_job = ProcessedJob.objects.create(
        job_posting=posting,
        clean_title="data engineer",
        clean_description="build python pipelines",
        role_category="Data Engineering",
        extracted_skills=[],
        skills_text="",
        skill_extraction_provider="groq",
        skill_extraction_error="returned no skills",
        created_at=now,
    )
    ExtractionResult.objects.create(
        processed_job=processed_job,
        provider="groq",
        model="llama-test",
        prompt_version="skill-extraction-v2",
        extracted_skills=[],
        error="returned no skills",
        created_at=now,
    )

    return run


def test_database_url_parses_postgresql_psycopg_urls():
    config = database_config_from_url(
        "postgresql+psycopg://user:pass@db:5432/joblens_ai"
    )

    assert config["ENGINE"] == "django.db.backends.postgresql"
    assert config["NAME"] == "joblens_ai"
    assert config["USER"] == "user"
    assert config["PASSWORD"] == "pass"
    assert config["HOST"] == "db"
    assert config["PORT"] == "5432"


def test_pipeline_models_are_unmanaged():
    assert Dataset._meta.managed is False
    assert IngestionRun._meta.managed is False
    assert ExtractionResult._meta.managed is False
    assert IngestionRun._meta.db_table == "ingestion_runs"
    assert ExtractionResult._meta.db_table == "extraction_results"


def test_health_endpoint_checks_database(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "django-ops",
        "database": "ok",
    }


def test_operations_route_requires_staff(client):
    response = client.get(reverse("operations-home"))

    assert response.status_code == 302
    assert reverse("operations-login") in response["Location"]


def test_operations_route_rejects_non_staff_user(client):
    user = User.objects.create_user(username="viewer", password="password")
    client.force_login(user)

    response = client.get(reverse("operations-home"))

    assert response.status_code == 403


def test_staff_operations_route_reads_pipeline_tables(
    client,
    seeded_pipeline_data,
):
    staff_user = User.objects.create_user(
        username="operator",
        password="password",
        is_staff=True,
    )
    ops_group = Group.objects.create(name=OPS_VIEWER_GROUP)
    staff_user.groups.add(ops_group)
    client.force_login(staff_user)

    response = client.get(reverse("operations-home"))
    body = response.content.decode()

    assert response.status_code == 200
    assert "Pipeline runs" in body
    assert "canada_jobs_fetch" in body
    assert "partial_success" in body
    assert "40/42" in body
    assert "Empty extractions" in body


def test_foundation_service_returns_pipeline_summary(seeded_pipeline_data):
    context = services.load_foundation_context()

    assert context["pipeline_run_count"] == 1
    assert context["latest_run"].source_type == "canada_jobs_fetch"
    assert context["empty_extraction_count"] == 1
