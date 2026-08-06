from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from django_ops.pipeline.auth import OPS_GROUPS


class Command(BaseCommand):
    help = "Create the Django operations access groups."

    def handle(self, *args: object, **options: object) -> None:
        for group_name in OPS_GROUPS:
            group, created = Group.objects.get_or_create(name=group_name)
            action = "created" if created else "exists"
            self.stdout.write(f"{group.name}: {action}")
