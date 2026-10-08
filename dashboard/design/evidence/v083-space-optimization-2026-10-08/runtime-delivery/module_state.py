"""Stable state envelope shared by dashboard providers."""

from __future__ import annotations

from typing import Any

STATE_VERSION = 1
STATUSES = frozenset({"active", "updating", "stale", "offline", "error", "unavailable"})


def module_state(
    *, status: str, source: str, updated_at: float = 0,
    data: dict[str, Any] | None = None, error: str = "",
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"Unknown module status: {status}")
    return {
        "version": STATE_VERSION,
        "status": status,
        "source": source,
        "updatedAt": updated_at,
        "data": data.copy() if data else {},
        "error": error,
    }
