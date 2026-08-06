from __future__ import annotations

from django.urls import path

from django_ops.pipeline import views


urlpatterns = [
    path("", views.redirect_to_operations),
    path("health/", views.health),
    path("ops/login/", views.OperationsLoginView.as_view(), name="operations-login"),
    path("ops/logout/", views.OperationsLogoutView.as_view(), name="operations-logout"),
    path("ops/", views.operations_home, name="operations-home"),
]
