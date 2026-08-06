from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import Group, User
from django.db import connection
from django.urls import reverse
from django.utils import timezone

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
def ops_user() -> User:
    user = User.objects.create_user(
        username="operator",
        password="password",
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=OPS_VIEWER_GROUP)
    user.groups.add(group)

    return user


@pytest.fixture()
def seeded_investigation_data(pipeline_tables):
    now = timezone.now()
    dataset = Dataset.objects.create(
        name="canada_jobs",
        source_type="canada_snapshot",
        created_at=now,
    )
    enrichment_run = IngestionRun.objects.create(
        dataset=dataset,
        source_type="canada_snapshot_enrichment",
        status="partial_success",
        started_at=now,
        completed_at=now + timedelta(minutes=5),
        total_sources=1,
        successful_sources=1,
        failed_sources=0,
        raw_job_count=60,
        processed_job_count=59,
        error_log=["greenhouse:geotab: no skills"],
        run_metadata={
            "dedup_rejected_count": 3,
            "provider_counts": {"groq": 58, "deterministic_fallback": 1},
            "model_counts": {"llama-3.3-70b-versatile": 58},
            "prompt_version_counts": {"skill-extraction-v2": 58},
            "source_results": [
                {
                    "company": "Example",
                    "source_type": "greenhouse",
                    "status": "succeeded",
                    "job_count": 60,
                    "error": "",
                }
            ],
        },
    )
    IngestionRun.objects.create(
        dataset=dataset,
        source_type="canada_jobs_fetch",
        status="succeeded",
        started_at=now - timedelta(hours=1),
        completed_at=now - timedelta(hours=1) + timedelta(seconds=20),
        total_sources=3,
        successful_sources=3,
        failed_sources=0,
        raw_job_count=100,
        processed_job_count=95,
        error_log=[],
        run_metadata={
            "source_results": [
                {
                    "company": "SearchCo",
                    "source_type": "ashby",
                    "status": "succeeded",
                    "job_count": 10,
                    "error": "",
                }
            ]
        },
    )
    for index in range(11):
        IngestionRun.objects.create(
            dataset=dataset,
            source_type=f"historical_fetch_{index}",
            status="succeeded",
            started_at=now - timedelta(days=index + 2),
            completed_at=now - timedelta(days=index + 2, seconds=-5),
            total_sources=1,
            successful_sources=1,
            failed_sources=0,
            raw_job_count=10,
            processed_job_count=10,
            error_log=[],
            run_metadata={},
        )

    posting = JobPosting.objects.create(
        dataset=dataset,
        job_id="job-empty",
        title="Data Engineer",
        company="Example",
        location="Toronto, ON",
        description="Build Python pipelines.",
        experience_level="Mid Level",
        source="greenhouse",
        source_url="https://example.com/jobs/empty",
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
    issue = ExtractionResult.objects.create(
        processed_job=processed_job,
        provider="groq",
        model="llama-3.3-70b-versatile",
        prompt_version="skill-extraction-v2",
        extracted_skills=[],
        error="returned no skills",
        created_at=now,
    )

    return {
        "dataset": dataset,
        "run": enrichment_run,
        "issue": issue,
    }


def test_pipeline_run_list_filters_and_paginates(
    client,
    ops_user,
    seeded_investigation_data,
):
    client.force_login(ops_user)

    response = client.get(
        reverse("pipeline-run-list"),
        {
            "status": "partial_success",
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "prompt_version": "skill-extraction-v2",
            "q": "geotab",
        },
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "1 matching runs" in body
    assert "canada_snapshot_enrichment" in body
    assert "canada_jobs_fetch" not in body

    page_two = client.get(reverse("pipeline-run-list"), {"page": "2"})

    assert page_two.status_code == 200
    assert "Page 2 of 2" in page_two.content.decode()


def test_pipeline_run_detail_shows_metadata_and_linked_posting_issue(
    client,
    ops_user,
    seeded_investigation_data,
):
    client.force_login(ops_user)
    run = seeded_investigation_data["run"]

    response = client.get(reverse("pipeline-run-detail", args=[run.id]))
    body = response.content.decode()

    assert response.status_code == 200
    assert "canada_snapshot_enrichment" in body
    assert "Dedup rejected" in body
    assert "llama-3.3-70b-versatile" in body
    assert "skill-extraction-v2" in body
    assert "Source Results" in body
    assert "Example" in body
    assert "Data Engineer" in body
    assert "https://example.com/jobs/empty" in body
    assert "returned no skills" in body


def test_extraction_issue_list_filters_and_searches(
    client,
    ops_user,
    seeded_investigation_data,
):
    client.force_login(ops_user)

    response = client.get(
        reverse("extraction-issue-list"),
        {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "prompt_version": "skill-extraction-v2",
            "q": "Data Engineer",
        },
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "1 matching issues" in body
    assert "Data Engineer" in body
    assert "Example" in body
    assert "returned no skills" in body

    no_match = client.get(reverse("extraction-issue-list"), {"q": "NoSuchCompany"})

    assert no_match.status_code == 200
    assert "0 matching issues" in no_match.content.decode()


def test_pipeline_run_services_filter_by_metadata(seeded_investigation_data):
    filters = services.PipelineRunFilters(
        status="partial_success",
        provider="groq",
        model="llama-3.3-70b-versatile",
        prompt_version="skill-extraction-v2",
        q="geotab",
    )

    assert services.run_matches_filters(seeded_investigation_data["run"], filters)


def test_pipeline_run_detail_missing_run_returns_404(client, ops_user, pipeline_tables):
    client.force_login(ops_user)

    response = client.get(reverse("pipeline-run-detail", args=[999]))

    assert response.status_code == 404
