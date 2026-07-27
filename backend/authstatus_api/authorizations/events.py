from __future__ import annotations

from typing import Any

from authstatus_api.authorizations.mappings import (
    auth_event_row_to_dict,
    prepare_auth_event_payload,
)
from authstatus_api.authorizations.sql import (
    insert_sql,
    sql_columns,
)
from authstatus_api.authorizations.state import (
    current_timestamp,
    sync_auth_timeline_fields,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db

AUTH_EVENT_TABLE_COLUMNS = {
    "id",
    "auth_id",
    "event_type",
    "event_date",
    "event_time",
    "outcome",
    "notes",
    "created_at",
    "updated_at",
    "requested_days",
    "approved_days",
    "auth_start_date",
    "auth_end_date",
    "review_due_date",
}


AUTH_EVENT_UPDATE_QUERIES = {
    "event_type": (
        "UPDATE auth_events SET event_type = ? " "WHERE auth_id = ? AND id = ?"
    ),
    "event_date": (
        "UPDATE auth_events SET event_date = ? " "WHERE auth_id = ? AND id = ?"
    ),
    "event_time": (
        "UPDATE auth_events SET event_time = ? " "WHERE auth_id = ? AND id = ?"
    ),
    "outcome": ("UPDATE auth_events SET outcome = ? " "WHERE auth_id = ? AND id = ?"),
    "notes": ("UPDATE auth_events SET notes = ? " "WHERE auth_id = ? AND id = ?"),
    "updated_at": (
        "UPDATE auth_events SET updated_at = ? " "WHERE auth_id = ? AND id = ?"
    ),
    "requested_days": (
        "UPDATE auth_events SET requested_days = ? " "WHERE auth_id = ? AND id = ?"
    ),
    "approved_days": (
        "UPDATE auth_events SET approved_days = ? " "WHERE auth_id = ? AND id = ?"
    ),
    "auth_start_date": (
        "UPDATE auth_events SET auth_start_date = ? " "WHERE auth_id = ? AND id = ?"
    ),
    "auth_end_date": (
        "UPDATE auth_events SET auth_end_date = ? " "WHERE auth_id = ? AND id = ?"
    ),
    "review_due_date": (
        "UPDATE auth_events SET review_due_date = ? " "WHERE auth_id = ? AND id = ?"
    ),
}


def _auth_exists(auth_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM auths WHERE id = ?",
            (auth_id,),
        ).fetchone()

    return row is not None


def create_auth_event(
    auth_id: int,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    init_db()

    if not _auth_exists(auth_id):
        return None

    now = current_timestamp()
    prepared = prepare_auth_event_payload(payload)
    prepared["auth_id"] = auth_id
    prepared["created_at"] = now
    prepared["updated_at"] = now

    keys = sql_columns(
        prepared,
        set(AUTH_EVENT_TABLE_COLUMNS),
        {"id"},
    )
    values = [prepared[key] for key in keys]

    with get_conn() as conn:
        cursor = conn.execute(
            insert_sql("auth_events", keys),
            values,
        )
        event_id = int(cursor.lastrowid)

    sync_auth_timeline_fields(auth_id)

    return get_auth_event(auth_id, event_id)


def list_auth_events(
    auth_id: int,
) -> list[dict[str, Any]] | None:
    init_db()

    if not _auth_exists(auth_id):
        return None

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM auth_events
            WHERE auth_id = ?
            ORDER BY event_date, event_time, id
            """,
            (auth_id,),
        ).fetchall()

    return [auth_event_row_to_dict(row) for row in rows]


def get_auth_event(
    auth_id: int,
    event_id: int,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM auth_events
            WHERE auth_id = ? AND id = ?
            """,
            (auth_id, event_id),
        ).fetchone()

    if row is None:
        return None

    return auth_event_row_to_dict(row)


def update_auth_event(
    auth_id: int,
    event_id: int,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    init_db()

    if get_auth_event(auth_id, event_id) is None:
        return None

    prepared = prepare_auth_event_payload(payload)
    prepared["updated_at"] = current_timestamp()

    keys = sql_columns(
        prepared,
        set(AUTH_EVENT_TABLE_COLUMNS),
        {"id", "auth_id", "created_at"},
    )

    if not keys:
        sync_auth_timeline_fields(auth_id)
        return get_auth_event(auth_id, event_id)

    with get_conn() as conn:
        for key in keys:
            conn.execute(
                AUTH_EVENT_UPDATE_QUERIES[key],
                (prepared[key], auth_id, event_id),
            )

    sync_auth_timeline_fields(auth_id)

    return get_auth_event(auth_id, event_id)


def delete_auth_event(
    auth_id: int,
    event_id: int,
) -> bool:
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            """
            DELETE FROM auth_events
            WHERE auth_id = ? AND id = ?
            """,
            (auth_id, event_id),
        )
        deleted = cursor.rowcount > 0

    if deleted:
        sync_auth_timeline_fields(auth_id)

    return deleted
