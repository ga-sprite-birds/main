"""Helpers for the API-wide response envelope."""

from typing import Any


def success(data: Any = None, msg: str = "ok") -> dict[str, Any]:
    """Return a successful response envelope."""
    return {
        "code": 0,
        "msg": msg,
        "data": {} if data is None else data,
    }


def fail(code: int, msg: str, data: Any = None) -> dict[str, Any]:
    """Return a failed response envelope."""
    return {
        "code": code,
        "msg": msg,
        "data": {} if data is None else data,
    }
