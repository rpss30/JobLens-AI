from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from django_ops.pipeline.auth import (
    can_manage_operations,
    operations_manager_required,
    operations_view_required,
)
from django_ops.pipeline.services import (
    OperationsActionError,
    check_database_connection,
    load_extraction_issues_context,
    load_foundation_context,
    load_pipeline_run_detail_context,
    load_pipeline_runs_context,
    mark_extraction_reviewed,
    request_extraction_retry,
    save_extraction_review_note,
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


def safe_operations_redirect(request: HttpRequest) -> str:
    next_url = request.POST.get("next") or reverse("extraction-issue-list")

    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url

    return reverse("extraction-issue-list")


@require_POST
@operations_manager_required
def extraction_issue_action(
    request: HttpRequest,
    result_id: int,
) -> HttpResponse:
    operation = request.POST.get("operation")

    try:
        if operation == "save_note":
            save_extraction_review_note(
                result_id=result_id,
                actor=request.user,
                note=request.POST.get("note", ""),
            )
            messages.success(request, "Review note saved.")
        elif operation == "mark_reviewed":
            mark_extraction_reviewed(
                result_id=result_id,
                actor=request.user,
                note=request.POST.get("note", ""),
            )
            messages.success(request, "Extraction marked as reviewed.")
        elif operation == "request_retry":
            request_extraction_retry(result_id=result_id, actor=request.user)
            messages.success(request, "Retry request recorded.")
        else:
            messages.error(request, "Unknown operation.")
    except OperationsActionError as error:
        messages.error(request, str(error))

    return redirect(safe_operations_redirect(request))
