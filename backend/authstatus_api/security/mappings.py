from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds")


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC)


def user_row_to_dict(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None

    user = dict(row)
    user["is_active"] = bool(user["is_active"])
    user["must_change_password"] = bool(user["must_change_password"])
    user["mfa_enabled"] = bool(user["mfa_enabled"])

    return user


def session_row_to_dict(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None

    return dict(row)
