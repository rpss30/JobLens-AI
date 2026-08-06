from __future__ import annotations

from django.urls import path

from django_ops.pipeline import views


urlpatterns = [
    path("", views.redirect_to_operations),
    path("health/", views.health),
    path("ops/", views.operations_home, name="operations-home"),
]
