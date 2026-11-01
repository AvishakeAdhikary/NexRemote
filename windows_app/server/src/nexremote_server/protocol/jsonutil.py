"""JSON helpers that mirror the legacy host's lenient field readers."""

from __future__ import annotations

import json
from typing import Any


def dumps(payload: Any) -> str:
    """Compact JSON with None-valued keys dropped (the legacy host used WhenWritingNull)."""
    return json.dumps(_strip_none(payload), separators=(",", ":"), ensure_ascii=False)


def _strip_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, (list, tuple)):
        return [_strip_none(v) for v in value]
    return value


def try_parse_object(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def get_str(msg: dict[str, Any], key: str, fallback: str = "") -> str:
    value = msg.get(key)
    return value if isinstance(value, str) else fallback


def get_int(msg: dict[str, Any], key: str, fallback: int = 0) -> int:
    value = msg.get(key)
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == value:  # not NaN
        return int(round(value))
    return fallback


def get_float(msg: dict[str, Any], key: str, fallback: float = 0.0) -> float:
    value = msg.get(key)
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        return float(value)
    return fallback


def get_bool(msg: dict[str, Any], key: str, fallback: bool = False) -> bool:
    value = msg.get(key)
    return value if isinstance(value, bool) else fallback


def get_int_list(msg: dict[str, Any], key: str) -> list[int]:
    value = msg.get(key)
    if not isinstance(value, list):
        return []
    return [int(v) for v in value if isinstance(v, int) and not isinstance(v, bool)]


def get_str_list(msg: dict[str, Any], key: str) -> list[str]:
    value = msg.get(key)
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str)]
