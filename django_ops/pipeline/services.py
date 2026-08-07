from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Page, Paginator
from django.db import DatabaseError, connection, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_ops.pipeline.models import (
    ExtractionResult,
    ExtractionReview,
    IngestionRun,
    OperationsAuditEvent,
)


DEFAULT_RUN_PAGE_SIZE = 10
DEFAULT_ISSUE_PAGE_SIZE = 15
MAX_FILTERED_RUNS = 500
MAX_REVIEW_NOTE_LENGTH = 2000
EXTRACTION_AUDIT_TARGET = "extraction_result"


@dataclass(frozen=True)
class PipelineRunFilters:
    status: str = ""
    provider: str = ""
    model: str = ""
    prompt_version: str = ""
    q: str = ""


@dataclass(frozen=True)
class ExtractionIssueFilters:
    provider: str = ""
    model: str = ""
    prompt_version: str = ""
    q: str = ""


class OperationsActionError(ValueError):
    pass


def check_database_connection() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except DatabaseError:
        return False


def load_foundation_context() -> dict[str, Any]:
    latest_run = (
        IngestionRun.objects.select_related("dataset")
        .order_by("-started_at")
        .first()
    )
    empty_extraction_count = ExtractionResult.objects.filter(
        extracted_skills=[],
    ).count()

    return {
        "pipeline_run_count": IngestionRun.objects.count(),
        "latest_run": latest_run,
        "empty_extraction_count": empty_extraction_count,
    }


def clean_query_value(value: object) -> str:
    return str(value or "").strip()


def positive_int(value: object, *, default: int = 1) -> int:
    try:
        parsed_value = int(str(value))
    except (TypeError, ValueError):
        return default

    return parsed_value if parsed_value > 0 else default


def pipeline_run_filters_from_query(params: Any) -> PipelineRunFilters:
    return PipelineRunFilters(
        status=clean_query_value(params.get("status")),
        provider=clean_query_value(params.get("provider")),
        model=clean_query_value(params.get("model")),
        prompt_version=clean_query_value(params.get("prompt_version")),
        q=clean_query_value(params.get("q")),
    )


def extraction_issue_filters_from_query(params: Any) -> ExtractionIssueFilters:
    return ExtractionIssueFilters(
        provider=clean_query_value(params.get("provider")),
        model=clean_query_value(params.get("model")),
        prompt_version=clean_query_value(params.get("prompt_version")),
        q=clean_query_value(params.get("q")),
    )


def metadata_counts(run: IngestionRun, key: str) -> dict[str, int]:
    metadata = run.run_metadata if isinstance(run.run_metadata, dict) else {}
    counts = metadata.get(key)

    if not isinstance(counts, dict):
        return {}

    return {
        str(count_key): int(count_value or 0)
        for count_key, count_value in counts.items()
        if str(count_key).strip()
    }


def source_results(run: IngestionRun) -> list[dict[str, Any]]:
    metadata = run.run_metadata if isinstance(run.run_metadata, dict) else {}
    results = metadata.get("source_results")

    return results if isinstance(results, list) else []


def metadata_has_value(run: IngestionRun, key: str, value: str) -> bool:
    if not value:
        return True

    normalized_value = value.strip().lower()
    return any(
        count_key.lower() == normalized_value
        for count_key in metadata_counts(run, key)
    )


def run_matches_search(run: IngestionRun, query: str) -> bool:
    if not query:
        return True

    normalized_query = query.lower()
    searchable_parts = [
        run.source_type,
        run.status,
        run.dataset.name if run.dataset else "",
        " ".join(str(item) for item in run.error_log or []),
    ]

    for result in source_results(run):
        searchable_parts.extend(
            [
                str(result.get("company", "")),
                str(result.get("source_type", "")),
                str(result.get("source_identifier", "")),
                str(result.get("error", "")),
            ]
        )

    return normalized_query in " ".join(searchable_parts).lower()


def run_matches_filters(run: IngestionRun, filters: PipelineRunFilters) -> bool:
    if filters.status and run.status != filters.status:
        return False

    if not metadata_has_value(run, "provider_counts", filters.provider):
        return False

    if not metadata_has_value(run, "model_counts", filters.model):
        return False

    if not metadata_has_value(
        run,
        "prompt_version_counts",
        filters.prompt_version,
    ):
        return False

    return run_matches_search(run, filters.q)


def paginate_items(
    items: list[Any],
    *,
    page_number: object,
    page_size: int,
) -> Page:
    paginator = Paginator(items, page_size)
    return paginator.get_page(positive_int(page_number))


def querystring_without_page(params: Any) -> str:
    query_pairs = []

    for key, values in params.lists():
        if key == "page":
            continue

        for value in values:
            if clean_query_value(value):
                query_pairs.append((key, value))

    return urlencode(query_pairs)


def run_filter_options() -> dict[str, list[str]]:
    runs = list(IngestionRun.objects.all()[:MAX_FILTERED_RUNS])

    return {
        "statuses": sorted({run.status for run in runs if run.status}),
        "providers": sorted(
            {
                provider
                for run in runs
                for provider in metadata_counts(run, "provider_counts")
            }
        ),
        "models": sorted(
            {
                model
                for run in runs
                for model in metadata_counts(run, "model_counts")
            }
        ),
        "prompt_versions": sorted(
            {
                prompt_version
                for run in runs
                for prompt_version in metadata_counts(run, "prompt_version_counts")
            }
        ),
    }


def load_pipeline_runs_context(params: Any) -> dict[str, Any]:
    filters = pipeline_run_filters_from_query(params)
    runs = list(
        IngestionRun.objects.select_related("dataset")
        .order_by("-started_at")[:MAX_FILTERED_RUNS]
    )
    filtered_runs = [
        run
        for run in runs
        if run_matches_filters(run, filters)
    ]
    page_obj = paginate_items(
        filtered_runs,
        page_number=params.get("page"),
        page_size=DEFAULT_RUN_PAGE_SIZE,
    )

    return {
        "filters": filters,
        "filter_options": run_filter_options(),
        "page_obj": page_obj,
        "pagination_query": querystring_without_page(params),
        "runs": page_obj.object_list,
        "total_matching_runs": len(filtered_runs),
    }


def extraction_issue_queryset():
    return (
        ExtractionResult.objects.select_related(
            "processed_job__job_posting",
            "processed_job__job_posting__dataset",
        )
        .filter(
            Q(extracted_skills=[])
            | (Q(error__isnull=False) & ~Q(error=""))
        )
        .order_by("-created_at")
    )


def actor_username(user: Any) -> str:
    username = getattr(user, "get_username", lambda: "")()
    return str(username or getattr(user, "username", "") or "unknown")


def clean_review_note(note: object) -> str:
    cleaned_note = clean_query_value(note)

    if len(cleaned_note) > MAX_REVIEW_NOTE_LENGTH:
        raise OperationsActionError(
            f"Review notes must be {MAX_REVIEW_NOTE_LENGTH} characters or fewer."
        )

    return cleaned_note


def extraction_issue_or_404(result_id: int) -> ExtractionResult:
    return get_object_or_404(extraction_issue_queryset(), pk=result_id)


def audit_metadata_for_extraction(result: ExtractionResult) -> dict[str, Any]:
    posting = result.processed_job.job_posting
    return {
        "posting_id": posting.id,
        "processed_job_id": result.processed_job_id,
        "title": posting.title,
        "company": posting.company,
        "source": posting.source,
        "provider": result.provider,
        "model": result.model,
        "prompt_version": result.prompt_version,
    }


def record_audit_event(
    *,
    actor: Any,
    action: str,
    result: ExtractionResult,
    metadata: dict[str, Any] | None = None,
) -> OperationsAuditEvent:
    event_metadata = audit_metadata_for_extraction(result)
    event_metadata.update(metadata or {})

    return OperationsAuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        actor_username=actor_username(actor),
        action=action,
        target_type=EXTRACTION_AUDIT_TARGET,
        target_id=result.id,
        metadata=event_metadata,
    )


def review_state_for_result(
    result: ExtractionResult,
) -> tuple[ExtractionReview, bool]:
    return ExtractionReview.objects.select_for_update().get_or_create(
        extraction_result_id=result.id,
    )


def attach_operation_state(issues: list[ExtractionResult]) -> list[ExtractionResult]:
    issue_ids = [issue.id for issue in issues]

    if not issue_ids:
        return issues

    reviews = {
        review.extraction_result_id: review
        for review in ExtractionReview.objects.filter(
            extraction_result_id__in=issue_ids,
        )
    }
    audits_by_target: dict[int, list[OperationsAuditEvent]] = {
        issue_id: [] for issue_id in issue_ids
    }

    for event in OperationsAuditEvent.objects.filter(
        target_type=EXTRACTION_AUDIT_TARGET,
        target_id__in=issue_ids,
    ).order_by("-created_at"):
        audits_by_target.setdefault(event.target_id, []).append(event)

    for issue in issues:
        issue.ops_review = reviews.get(issue.id)
        issue.ops_audit_events = audits_by_target.get(issue.id, [])

    return issues


@transaction.atomic
def save_extraction_review_note(
    *,
    result_id: int,
    actor: Any,
    note: object,
) -> ExtractionReview:
    result = extraction_issue_or_404(result_id)
    review, _ = review_state_for_result(result)
    now = timezone.now()

    review.note = clean_review_note(note)
    review.note_updated_by = actor
    review.note_updated_by_username = actor_username(actor)
    review.note_updated_at = now
    review.save(
        update_fields=[
            "note",
            "note_updated_by",
            "note_updated_by_username",
            "note_updated_at",
            "updated_at",
        ]
    )
    record_audit_event(
        actor=actor,
        action=OperationsAuditEvent.ACTION_NOTE_SAVED,
        result=result,
        metadata={"note_length": len(review.note)},
    )

    return review


@transaction.atomic
def mark_extraction_reviewed(
    *,
    result_id: int,
    actor: Any,
    note: object = "",
) -> ExtractionReview:
    result = extraction_issue_or_404(result_id)
    review, _ = review_state_for_result(result)
    now = timezone.now()
    cleaned_note = clean_review_note(note)
    update_fields = [
        "status",
        "reviewed_by",
        "reviewed_by_username",
        "reviewed_at",
        "updated_at",
    ]

    review.status = ExtractionReview.STATUS_REVIEWED
    review.reviewed_by = actor
    review.reviewed_by_username = actor_username(actor)
    review.reviewed_at = now

    if cleaned_note:
        review.note = cleaned_note
        review.note_updated_by = actor
        review.note_updated_by_username = actor_username(actor)
        review.note_updated_at = now
        update_fields.extend(
            [
                "note",
                "note_updated_by",
                "note_updated_by_username",
                "note_updated_at",
            ]
        )

    review.save(update_fields=update_fields)
    record_audit_event(
        actor=actor,
        action=OperationsAuditEvent.ACTION_MARKED_REVIEWED,
        result=result,
        metadata={"note_updated": bool(cleaned_note)},
    )

    return review


@transaction.atomic
def request_extraction_retry(
    *,
    result_id: int,
    actor: Any,
) -> ExtractionReview:
    result = extraction_issue_or_404(result_id)
    review, _ = review_state_for_result(result)

    if review.retry_requested_at:
        raise OperationsActionError("A retry has already been requested.")

    review.retry_status = ExtractionReview.RETRY_STATUS_REQUESTED
    review.retry_requested_by = actor
    review.retry_requested_by_username = actor_username(actor)
    review.retry_requested_at = timezone.now()
    review.save(
        update_fields=[
            "retry_status",
            "retry_requested_by",
            "retry_requested_by_username",
            "retry_requested_at",
            "updated_at",
        ]
    )
    record_audit_event(
        actor=actor,
        action=OperationsAuditEvent.ACTION_RETRY_REQUESTED,
        result=result,
    )

    return review


def extraction_issue_matches_search(result: ExtractionResult, query: str) -> bool:
    if not query:
        return True

    posting = result.processed_job.job_posting
    searchable_text = " ".join(
        [
            posting.title,
            posting.company,
            posting.source or "",
            posting.source_url or "",
            result.provider,
            result.model or "",
            result.prompt_version or "",
            result.error or "",
        ]
    )
    return query.lower() in searchable_text.lower()


def load_extraction_issues(
    *,
    filters: ExtractionIssueFilters | None = None,
    dataset_id: int | None = None,
    limit: int | None = None,
) -> list[ExtractionResult]:
    filters = filters or ExtractionIssueFilters()
    queryset = extraction_issue_queryset()

    if dataset_id is not None:
        queryset = queryset.filter(processed_job__job_posting__dataset_id=dataset_id)

    if filters.provider:
        queryset = queryset.filter(provider=filters.provider)

    if filters.model:
        queryset = queryset.filter(model=filters.model)

    if filters.prompt_version:
        queryset = queryset.filter(prompt_version=filters.prompt_version)

    results = list(queryset[: MAX_FILTERED_RUNS if limit is None else limit])

    if filters.q:
        results = [
            result
            for result in results
            if extraction_issue_matches_search(result, filters.q)
        ]

    return attach_operation_state(results)


def extraction_filter_options() -> dict[str, list[str]]:
    queryset = extraction_issue_queryset()
    return {
        "providers": sorted(
            {
                provider
                for provider in queryset.values_list("provider", flat=True)
                if provider
            }
        ),
        "models": sorted(
            {
                model
                for model in queryset.values_list("model", flat=True)
                if model
            }
        ),
        "prompt_versions": sorted(
            {
                prompt_version
                for prompt_version in queryset.values_list(
                    "prompt_version",
                    flat=True,
                )
                if prompt_version
            }
        ),
    }


def load_extraction_issues_context(params: Any) -> dict[str, Any]:
    filters = extraction_issue_filters_from_query(params)
    issues = load_extraction_issues(filters=filters)
    page_obj = paginate_items(
        issues,
        page_number=params.get("page"),
        page_size=DEFAULT_ISSUE_PAGE_SIZE,
    )

    return {
        "filters": filters,
        "filter_options": extraction_filter_options(),
        "page_obj": page_obj,
        "pagination_query": querystring_without_page(params),
        "issues": page_obj.object_list,
        "total_matching_issues": len(issues),
    }


def load_pipeline_run_detail_context(run_id: int) -> dict[str, Any]:
    run = get_object_or_404(
        IngestionRun.objects.select_related("dataset"),
        pk=run_id,
    )
    extraction_issues = load_extraction_issues(
        dataset_id=run.dataset_id,
        limit=25,
    )

    return {
        "run": run,
        "source_results": source_results(run),
        "provider_counts": metadata_counts(run, "provider_counts"),
        "model_counts": metadata_counts(run, "model_counts"),
        "prompt_version_counts": metadata_counts(run, "prompt_version_counts"),
        "dedup_rejected_count": (
            run.run_metadata.get("dedup_rejected_count", 0)
            if isinstance(run.run_metadata, dict)
            else 0
        ),
        "extraction_issues": extraction_issues,
    }
