from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from django_ops.pipeline.services import (
    check_database_connection,
    load_foundation_context,
)


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    if not check_database_connection():
        return JsonResponse(
            {
                "status": "error",
                "service": "django-ops",
                "database": "unavailable",
            },
            status=503,
        )

    return JsonResponse(
        {
            "status": "ok",
            "service": "django-ops",
            "database": "ok",
        }
    )


@require_GET
def redirect_to_operations(request: HttpRequest) -> HttpResponse:
    return redirect("operations-home")


@staff_member_required(login_url="/admin/login/")
def operations_home(request: HttpRequest) -> HttpResponse:
    try:
        context = {
            "database_ready": True,
            **load_foundation_context(),
        }
    except DatabaseError as error:
        context = {
            "database_ready": False,
            "database_error": str(error),
            "pipeline_run_count": 0,
            "latest_run": None,
            "empty_extraction_count": 0,
        }

    return render(request, "pipeline/operations_home.html", context)
