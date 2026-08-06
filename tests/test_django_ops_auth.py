from __future__ import annotations

import pytest
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from django_ops.pipeline.auth import (
    OPS_MANAGER_GROUP,
    OPS_VIEWER_GROUP,
    can_manage_operations,
    can_view_operations,
)


pytestmark = pytest.mark.django_db


def create_user(
    *,
    username: str,
    is_staff: bool = True,
    is_superuser: bool = False,
    group_name: str | None = None,
) -> User:
    user = User.objects.create_user(
        username=username,
        password="password",
        is_staff=is_staff,
        is_superuser=is_superuser,
    )

    if group_name:
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)

    return user


def test_operations_login_page_renders_csrf_token(client):
    response = client.get(reverse("operations-login"))
    body = response.content.decode()

    assert response.status_code == 200
    assert "Operations Login" in body
    assert "csrfmiddlewaretoken" in body


def test_operations_login_redirects_valid_viewer(client):
    create_user(username="operator", group_name=OPS_VIEWER_GROUP)

    response = client.post(
        reverse("operations-login"),
        {
            "username": "operator",
            "password": "password",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("operations-home")


def test_authenticated_staff_without_ops_group_gets_forbidden(client):
    user = create_user(username="staff-without-role")
    client.force_login(user)

    response = client.get(reverse("operations-home"))

    assert response.status_code == 403
    assert "Operations access required" in response.content.decode()


def test_viewer_and_manager_roles_can_view_operations(client, monkeypatch):
    monkeypatch.setattr(
        "django_ops.pipeline.views.load_foundation_context",
        lambda: {
            "pipeline_run_count": 0,
            "latest_run": None,
            "empty_extraction_count": 0,
        },
    )
    viewer = create_user(username="viewer", group_name=OPS_VIEWER_GROUP)
    manager = create_user(username="manager", group_name=OPS_MANAGER_GROUP)

    assert can_view_operations(viewer) is True
    assert can_manage_operations(viewer) is False
    assert can_view_operations(manager) is True
    assert can_manage_operations(manager) is True

    client.force_login(viewer)
    viewer_response = client.get(reverse("operations-home"))

    client.force_login(manager)
    manager_response = client.get(reverse("operations-home"))

    assert viewer_response.status_code == 200
    assert "Viewer access enabled." in viewer_response.content.decode()
    assert manager_response.status_code == 200
    assert "Manager access enabled." in manager_response.content.decode()


def test_superuser_has_manager_access():
    superuser = create_user(username="owner", is_superuser=True)

    assert can_view_operations(superuser) is True
    assert can_manage_operations(superuser) is True


def test_logout_requires_post(client):
    user = create_user(username="operator", group_name=OPS_VIEWER_GROUP)
    client.force_login(user)

    response = client.get(reverse("operations-logout"))

    assert response.status_code == 405


def test_logout_post_signs_user_out(client):
    user = create_user(username="operator", group_name=OPS_VIEWER_GROUP)
    client.force_login(user)

    response = client.post(reverse("operations-logout"))
    follow_up = client.get(reverse("operations-home"))

    assert response.status_code == 302
    assert response["Location"] == reverse("operations-login")
    assert follow_up.status_code == 302
    assert reverse("operations-login") in follow_up["Location"]


def test_logout_post_is_csrf_protected():
    user = create_user(username="operator", group_name=OPS_VIEWER_GROUP)
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(user)

    response = csrf_client.post(reverse("operations-logout"))

    assert response.status_code == 403


def test_session_cookie_settings_are_hardened():
    assert settings.SESSION_COOKIE_NAME == "joblens_ops_sessionid"
    assert settings.CSRF_COOKIE_NAME == "joblens_ops_csrftoken"
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE == "Lax"
    assert settings.CSRF_COOKIE_SAMESITE == "Lax"
    assert settings.SESSION_COOKIE_AGE == 28800


def test_bootstrap_ops_roles_command_creates_groups():
    call_command("bootstrap_ops_roles", verbosity=0)

    assert Group.objects.filter(name=OPS_VIEWER_GROUP).exists()
    assert Group.objects.filter(name=OPS_MANAGER_GROUP).exists()
