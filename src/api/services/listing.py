from collections.abc import Sequence
from typing import Any


def filter_items(
    items: Sequence[dict[str, Any]],
    filters: dict[str, str | None],
) -> list[dict[str, Any]]:
    filtered_items = list(items)

    for field_name, expected_value in filters.items():
        if expected_value is None:
            continue

        normalized_expected_value = expected_value.strip().lower()

        if not normalized_expected_value:
            continue

        filtered_items = [
            item
            for item in filtered_items
            if str(item.get(field_name, "")).strip().lower()
            == normalized_expected_value
        ]

    return filtered_items


def sort_items(
    items: Sequence[dict[str, Any]],
    *,
    sort_by: str,
    sort_order: str,
) -> list[dict[str, Any]]:
    reverse = sort_order == "desc"

    return sorted(
        items,
        key=lambda item: (
            item.get(sort_by) is None,
            item.get(sort_by),
        ),
        reverse=reverse,
    )


def paginate_items(
    items: Sequence[dict[str, Any]],
    *,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    return list(items)[offset : offset + limit]
