from __future__ import annotations

from django.contrib.auth.views import LoginView, LogoutView
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET

from django_ops.pipeline.auth import can_manage_operations, operations_view_required
from django_ops.pipeline.services import (
    check_database_connection,
    load_extraction_issues_context,
    load_foundation_context,
    load_pipeline_run_detail_context,
    load_pipeline_runs_context,
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


class OperationsLoginView(LoginView):
    template_name = "pipeline/login.html"
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        return self.get_redirect_url() or str(reverse_lazy("operations-home"))


class OperationsLogoutView(LogoutView):
    next_page = reverse_lazy("operations-login")


@operations_view_required
def operations_home(request: HttpRequest) -> HttpResponse:
    try:
        context = {
            "database_ready": True,
            "can_manage_operations": can_manage_operations(request.user),
            **load_foundation_context(),
        }
    except DatabaseError as error:
        context = {
            "database_ready": False,
            "can_manage_operations": can_manage_operations(request.user),
            "database_error": str(error),
            "pipeline_run_count": 0,
            "latest_run": None,
            "empty_extraction_count": 0,
        }

    return render(request, "pipeline/operations_home.html", context)


@operations_view_required
def pipeline_run_list(request: HttpRequest) -> HttpResponse:
    context = {
        "can_manage_operations": can_manage_operations(request.user),
        **load_pipeline_runs_context(request.GET),
    }
    return render(request, "pipeline/run_list.html", context)


@operations_view_required
def pipeline_run_detail(request: HttpRequest, run_id: int) -> HttpResponse:
    context = {
        "can_manage_operations": can_manage_operations(request.user),
        **load_pipeline_run_detail_context(run_id),
    }
    return render(request, "pipeline/run_detail.html", context)


@operations_view_required
def extraction_issue_list(request: HttpRequest) -> HttpResponse:
    context = {
        "can_manage_operations": can_manage_operations(request.user),
        **load_extraction_issues_context(request.GET),
    }
    return render(request, "pipeline/extraction_issue_list.html", context)
