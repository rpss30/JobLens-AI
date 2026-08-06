from __future__ import annotations

from typing import Any

from django.db import DatabaseError, connection

from django_ops.pipeline.models import ExtractionResult, IngestionRun


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
