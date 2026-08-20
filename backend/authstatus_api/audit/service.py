from __future__ import annotations

import hmac
import json
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from authstatus_api.audit.chain import (
    AUDIT_CHAIN_GENESIS,
    hash_audit_chain_state,
    hash_audit_event,
)
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
    serialized_metadata = _safe_metadata(metadata)
    ip_address = _client_ip(request)
    user_agent = _user_agent(request)

    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")

        chain_state = conn.execute("""
            SELECT
                head_event_id,
                head_event_hash,
                state_hash
            FROM audit_chain_state
            WHERE id = 1
            """).fetchone()

        if chain_state is None:
            previous_hash = AUDIT_CHAIN_GENESIS
        else:
            expected_state_hash = hash_audit_chain_state(
                head_event_id=chain_state["head_event_id"],
                head_event_hash=chain_state["head_event_hash"],
            )

            if not hmac.compare_digest(
                chain_state["state_hash"],
                expected_state_hash,
            ):
                raise RuntimeError("Audit chain state integrity check failed.")

            head_row = conn.execute(
                """
                SELECT event_hash
                FROM audit_events
                WHERE id = ?
                """,
                (chain_state["head_event_id"],),
            ).fetchone()

            if (
                head_row is None
                or head_row["event_hash"] != chain_state["head_event_hash"]
            ):
                raise RuntimeError("Audit chain head integrity check failed.")

            previous_hash = chain_state["head_event_hash"]

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
                created_at,
                previous_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                audit_username,
                action,
                resource_type,
                resource_id,
                serialized_metadata,
                ip_address,
                user_agent,
                created_at,
                previous_hash,
            ),
        )

        audit_id = int(cursor.lastrowid)

        event_hash = hash_audit_event(
            event_id=audit_id,
            user_id=user_id,
            username=audit_username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=serialized_metadata,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=created_at,
            previous_hash=previous_hash,
        )

        conn.execute(
            """
            UPDATE audit_events
            SET event_hash = ?
            WHERE id = ?
            """,
            (
                event_hash,
                audit_id,
            ),
        )

        state_hash = hash_audit_chain_state(
            head_event_id=audit_id,
            head_event_hash=event_hash,
        )

        state_cursor = conn.execute(
            """
            UPDATE audit_chain_state
            SET
                head_event_id = ?,
                head_event_hash = ?,
                state_hash = ?
            WHERE id = 1
            """,
            (
                audit_id,
                event_hash,
                state_hash,
            ),
        )

        if state_cursor.rowcount == 0:
            conn.execute(
                """
                INSERT INTO audit_chain_state (
                    id,
                    head_event_id,
                    head_event_hash,
                    state_hash
                )
                VALUES (1, ?, ?, ?)
                """,
                (
                    audit_id,
                    event_hash,
                    state_hash,
                ),
            )

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
