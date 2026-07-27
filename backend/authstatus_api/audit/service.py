from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _client_ip(request: Request | None) -> str:
    if request is None or request.client is None:
        return ""

    return request.client.host


def _user_agent(request: Request | None) -> str:
    if request is None:
        return ""

    return request.headers.get("user-agent", "")


def _safe_metadata(metadata: dict[str, Any] | None) -> str:
    return json.dumps(metadata or {}, sort_keys=True)


def _contains_pattern(value: str) -> str:
    escaped_value = (
        value.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )

    return f"%{escaped_value}%"


def audit_field_names(payload: dict[str, Any]) -> dict[str, list[str]]:
    return {"fields": sorted(payload.keys())}


def record_audit_event(
    *,
    action: str,
    resource_type: str,
    user: dict[str, Any] | None = None,
    resource_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    request: Request | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    init_db()

    created_at = _now()
    user_id = user["id"] if user else None
    audit_username = username or (user["username"] if user else None)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_events (
                user_id,
                username,
                action,
                resource_type,
                resource_id,
                metadata,
                ip_address,
                user_agent,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                audit_username,
                action,
                resource_type,
                resource_id,
                _safe_metadata(metadata),
                _client_ip(request),
                _user_agent(request),
                created_at,
            ),
        )

        audit_id = int(cursor.lastrowid)
        row = conn.execute(
            """
            SELECT *
            FROM audit_events
            WHERE id = ?
            """,
            (audit_id,),
        ).fetchone()

    return dict(row)


def list_audit_events(
    *,
    page: int = 1,
    page_size: int = 50,
    action: str | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    init_db()

    action_pattern = (
        _contains_pattern(action) if action is not None and action.strip() else None
    )
    username_pattern = (
        _contains_pattern(username)
        if username is not None and username.strip()
        else None
    )

    filter_values = [
        action_pattern,
        action_pattern,
        username_pattern,
        username_pattern,
    ]
    offset = (page - 1) * page_size

    with get_conn() as conn:
        total = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM audit_events
            WHERE (
                ? IS NULL
                OR LOWER(action) LIKE LOWER(?) ESCAPE '\\'
            )
            AND (
                ? IS NULL
                OR LOWER(username) LIKE LOWER(?) ESCAPE '\\'
            )
            """,
            filter_values,
        ).fetchone()["total"]

        rows = conn.execute(
            """
            SELECT
                id,
                user_id,
                username,
                action,
                resource_type,
                resource_id,
                metadata,
                ip_address,
                user_agent,
                created_at
            FROM audit_events
            WHERE (
                ? IS NULL
                OR LOWER(action) LIKE LOWER(?) ESCAPE '\\'
            )
            AND (
                ? IS NULL
                OR LOWER(username) LIKE LOWER(?) ESCAPE '\\'
            )
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            [*filter_values, page_size, offset],
        ).fetchall()

    return {
        "events": [dict(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
