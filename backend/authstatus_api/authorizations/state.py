from __future__ import annotations

from datetime import datetime
from typing import Any

from authstatus_api.authorizations.mappings import (
    auth_event_row_to_dict,
)
from authstatus_api.authorizations.timeline import (
    current_auth_snapshot,
    event_datetime_value,
    is_request_submitted_event,
    is_terminal_event,
)
from authstatus_api.persistence.connections import get_conn


def current_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def has_decision(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status") or "").strip().lower()
    approved_days = payload.get("approved_days")

    if status in {"approved", "denied", "appealed", "p2p"}:
        return True

    if approved_days is None:
        return False

    try:
        return int(approved_days) > 0
    except (TypeError, ValueError):
        return False


def initial_timeline_event_payload(
    auth_record: dict[str, Any],
) -> dict[str, Any]:
    event_date = str(auth_record.get("auth_start_date") or "").strip()

    if not event_date:
        event_date = str(auth_record.get("created_at") or current_timestamp())[:10]

    return {
        "event_type": "Initial Authorization",
        "event_date": event_date,
        "event_time": "",
        "outcome": str(auth_record.get("status") or "Pending"),
        "notes": ("Initial authorization created from auth entry."),
        "requested_days": int(auth_record.get("requested_days") or 0),
        "approved_days": int(auth_record.get("approved_days") or 0),
        "auth_start_date": str(auth_record.get("auth_start_date") or ""),
        "auth_end_date": str(auth_record.get("auth_end_date") or ""),
        "review_due_date": str(auth_record.get("review_due_date") or ""),
    }


def sync_auth_timeline_fields(auth_id: int) -> None:
    with get_conn() as conn:
        auth_row = conn.execute(
            """
            SELECT decision_at
            FROM auths
            WHERE id = ?
            """,
            (auth_id,),
        ).fetchone()

        existing_decision_at = (
            str(auth_row["decision_at"]).strip()
            if auth_row is not None and auth_row["decision_at"] is not None
            else ""
        )
        rows = conn.execute(
            """
            SELECT *
            FROM auth_events
            WHERE auth_id = ?
            ORDER BY event_date, event_time, id
            """,
            (auth_id,),
        ).fetchall()

        events = [auth_event_row_to_dict(row) for row in rows]

        submitted_at = next(
            (
                event_datetime_value(event)
                for event in events
                if is_request_submitted_event(event)
            ),
            None,
        )

        if submitted_at is None and events:
            submitted_at = event_datetime_value(events[0]) or None

        timeline_decision_at = next(
            (
                event_datetime_value(event)
                for event in events
                if is_terminal_event(event)
            ),
            None,
        )

        decision_at = existing_decision_at or timeline_decision_at

        snapshot = current_auth_snapshot(events)

        conn.execute(
            """
            UPDATE auths
            SET
                submitted_at = ?,
                decision_at = ?,
                status = ?,
                requested_days = COALESCE(?, requested_days),
                approved_days = COALESCE(?, approved_days),
                auth_start_date = COALESCE(?, auth_start_date),
                auth_end_date = COALESCE(?, auth_end_date),
                review_due_date = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                submitted_at,
                decision_at,
                snapshot["status"],
                snapshot["requested_days"],
                snapshot["approved_days"],
                snapshot["auth_start_date"],
                snapshot["auth_end_date"],
                snapshot["review_due_date"],
                current_timestamp(),
                auth_id,
            ),
        )
