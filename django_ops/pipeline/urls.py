from __future__ import annotations

from django.urls import path

from django_ops.pipeline import views


urlpatterns = [
    path("", views.redirect_to_operations),
    path("health/", views.health),
    path("ops/login/", views.OperationsLoginView.as_view(), name="operations-login"),
    path("ops/logout/", views.OperationsLogoutView.as_view(), name="operations-logout"),
    path("ops/", views.operations_home, name="operations-home"),
    path("ops/runs/", views.pipeline_run_list, name="pipeline-run-list"),
    path(
        "ops/runs/<int:run_id>/",
        views.pipeline_run_detail,
        name="pipeline-run-detail",
    ),
    path(
        "ops/extractions/issues/",
        views.extraction_issue_list,
        name="extraction-issue-list",
    ),
]
