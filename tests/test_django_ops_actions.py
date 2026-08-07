from __future__ import annotations

import pytest
from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from django_ops.pipeline.auth import OPS_MANAGER_GROUP, OPS_VIEWER_GROUP
from django_ops.pipeline.models import (
    Dataset,
    ExtractionResult,
    ExtractionReview,
    IngestionRun,
    JobPosting,
    OperationsAuditEvent,
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


def create_ops_user(*, username: str, group_name: str) -> User:
    user = User.objects.create_user(
        username=username,
        password="password",
        is_staff=True,
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)

    return user


@pytest.fixture()
def manager_user() -> User:
    return create_ops_user(username="manager", group_name=OPS_MANAGER_GROUP)


@pytest.fixture()
def viewer_user() -> User:
    return create_ops_user(username="viewer", group_name=OPS_VIEWER_GROUP)


@pytest.fixture()
def extraction_issue(pipeline_tables) -> ExtractionResult:
    now = timezone.now()
    dataset = Dataset.objects.create(
        name="canada_jobs",
        source_type="canada_snapshot",
        created_at=now,
    )
    IngestionRun.objects.create(
        dataset=dataset,
        source_type="canada_snapshot_enrichment",
        status="partial_success",
        started_at=now,
        completed_at=now,
        total_sources=1,
        successful_sources=1,
        failed_sources=0,
        raw_job_count=1,
        processed_job_count=1,
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

    return ExtractionResult.objects.create(
        processed_job=processed_job,
        provider="groq",
        model="llama-test",
        prompt_version="skill-extraction-v2",
        extracted_skills=[],
        error="returned no skills",
        created_at=now,
    )


def test_viewer_cannot_post_extraction_actions(client, viewer_user, extraction_issue):
    client.force_login(viewer_user)

    response = client.post(
        reverse("extraction-issue-action", args=[extraction_issue.id]),
        {"operation": "mark_reviewed"},
    )

    assert response.status_code == 403
    assert ExtractionReview.objects.count() == 0
    assert OperationsAuditEvent.objects.count() == 0


def test_manager_saves_review_note_and_audit_event(
    client,
    manager_user,
    extraction_issue,
):
    client.force_login(manager_user)

    response = client.post(
        reverse("extraction-issue-action", args=[extraction_issue.id]),
        {
            "operation": "save_note",
            "note": "Prompt returned an empty list; inspect before next refresh.",
            "next": reverse("extraction-issue-list"),
        },
    )

    review = ExtractionReview.objects.get(extraction_result_id=extraction_issue.id)
    audit = OperationsAuditEvent.objects.get()

    assert response.status_code == 302
    assert response["Location"] == reverse("extraction-issue-list")
    assert review.note == "Prompt returned an empty list; inspect before next refresh."
    assert review.note_updated_by == manager_user
    assert review.note_updated_by_username == "manager"
    assert audit.action == OperationsAuditEvent.ACTION_NOTE_SAVED
    assert audit.actor == manager_user
    assert audit.metadata["company"] == "Example"
    assert audit.metadata["note_length"] == len(review.note)


def test_manager_marks_extraction_reviewed(client, manager_user, extraction_issue):
    client.force_login(manager_user)

    response = client.post(
        reverse("extraction-issue-action", args=[extraction_issue.id]),
        {
            "operation": "mark_reviewed",
            "note": "Known low-signal posting.",
        },
        follow=True,
    )

    review = ExtractionReview.objects.get(extraction_result_id=extraction_issue.id)
    audit = OperationsAuditEvent.objects.get(
        action=OperationsAuditEvent.ACTION_MARKED_REVIEWED,
    )

    assert response.status_code == 200
    assert review.status == ExtractionReview.STATUS_REVIEWED
    assert review.reviewed_by == manager_user
    assert review.reviewed_by_username == "manager"
    assert review.note == "Known low-signal posting."
    assert audit.target_id == extraction_issue.id
    assert "reviewed" in response.content.decode()


def test_retry_request_is_single_and_audited(client, manager_user, extraction_issue):
    client.force_login(manager_user)

    first_response = client.post(
        reverse("extraction-issue-action", args=[extraction_issue.id]),
        {"operation": "request_retry"},
    )
    second_response = client.post(
        reverse("extraction-issue-action", args=[extraction_issue.id]),
        {"operation": "request_retry"},
        follow=True,
    )

    review = ExtractionReview.objects.get(extraction_result_id=extraction_issue.id)

    assert first_response.status_code == 302
    assert second_response.status_code == 200
    assert review.retry_status == ExtractionReview.RETRY_STATUS_REQUESTED
    assert review.retry_requested_by == manager_user
    assert review.retry_requested_by_username == "manager"
    assert OperationsAuditEvent.objects.filter(
        action=OperationsAuditEvent.ACTION_RETRY_REQUESTED,
        target_id=extraction_issue.id,
    ).count() == 1
    assert "A retry has already been requested." in second_response.content.decode()


def test_extraction_action_requires_csrf(manager_user, extraction_issue):
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(manager_user)

    response = csrf_client.post(
        reverse("extraction-issue-action", args=[extraction_issue.id]),
        {"operation": "save_note", "note": "Needs review."},
    )

    assert response.status_code == 403
    assert ExtractionReview.objects.count() == 0
    assert OperationsAuditEvent.objects.count() == 0


def test_run_detail_shows_review_state_and_audit_trail(
    client,
    manager_user,
    extraction_issue,
):
    client.force_login(manager_user)
    run_id = IngestionRun.objects.get().id
    ExtractionReview.objects.create(
        extraction_result_id=extraction_issue.id,
        status=ExtractionReview.STATUS_REVIEWED,
        note="Reviewed from the issue queue.",
        reviewed_by=manager_user,
        reviewed_by_username="manager",
        reviewed_at=timezone.now(),
    )
    OperationsAuditEvent.objects.create(
        actor=manager_user,
        actor_username="manager",
        action=OperationsAuditEvent.ACTION_MARKED_REVIEWED,
        target_type="extraction_result",
        target_id=extraction_issue.id,
        metadata={"company": "Example"},
    )

    response = client.get(reverse("pipeline-run-detail", args=[run_id]))
    body = response.content.decode()

    assert response.status_code == 200
    assert "Reviewed from the issue queue." in body
    assert "extraction_marked_reviewed by manager" in body
