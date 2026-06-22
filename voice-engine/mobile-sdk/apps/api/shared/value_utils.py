from __future__ import annotations

from typing import Any


def to_bool(value: Any, fallback: bool = False) -> bool:
    return value if isinstance(value, bool) else fallback


def to_string_value(value: Any, fallback: str = "") -> str:
    return value.strip() if isinstance(value, str) else fallback


def to_int_in_range(value: Any, fallback: int, minimum: int, maximum: int) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback

    if number != number or number in (float("inf"), float("-inf")):
        return fallback

    return min(maximum, max(minimum, round(number)))

