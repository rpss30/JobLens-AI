from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse


OPS_VIEWER_GROUP = "JobLens Ops Viewers"
OPS_MANAGER_GROUP = "JobLens Ops Managers"
OPS_GROUPS = (OPS_VIEWER_GROUP, OPS_MANAGER_GROUP)


def is_staff_operations_user(user: Any) -> bool:
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
    )


def user_has_group(user: Any, group_name: str) -> bool:
    return bool(user.groups.filter(name=group_name).exists())


def can_view_operations(user: Any) -> bool:
    if not is_staff_operations_user(user):
        return False

    return bool(
        user.is_superuser
        or user_has_group(user, OPS_VIEWER_GROUP)
        or user_has_group(user, OPS_MANAGER_GROUP)
    )


def can_manage_operations(user: Any) -> bool:
    if not is_staff_operations_user(user):
        return False

    return bool(user.is_superuser or user_has_group(user, OPS_MANAGER_GROUP))


def operations_view_required(
    view_func: Callable[..., HttpResponse],
) -> Callable[..., HttpResponse]:
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                login_url=reverse("operations-login"),
            )

        if not can_view_operations(request.user):
            return render(
                request,
                "pipeline/forbidden.html",
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return wrapper
