from __future__ import annotations

from typing import Any

from authstatus_api.authorizations.events import (
    create_auth_event,
)
from authstatus_api.authorizations.mappings import (
    auth_row_to_dict,
    prepare_auth_payload,
)
from authstatus_api.authorizations.sql import (
    insert_sql,
    sql_columns,
    update_assignments,
)
from authstatus_api.authorizations.state import (
    current_timestamp,
    has_decision,
    initial_timeline_event_payload,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db

AUTH_TABLE_COLUMNS = {
    "id",
    "facility",
    "client_name",
    "member_id",
    "group_number",
    "date_of_birth",
    "loc",
    "insurance",
    "insurance_phone",
    "insurance_fax",
    "submission_methods",
    "portal_name",
    "fax_numbers",
    "live_call_type",
    "scheduled_call_at",
    "care_manager_enabled",
    "care_manager_details",
    "notes_links",
    "auth_type",
    "status",
    "discharge_clinical_needed",
    "no_pa_required",
    "progress_made",
    "facility_informed",
    "waiting_on_clinicals",
    "los_requested",
    "days_approved",
    "requested_days",
    "approved_days",
    "auth_start_date",
    "auth_end_date",
    "programming_days",
    "review_due_date",
    "submitted_at",
    "decision_at",
    "created_at",
    "updated_at",
}


def create_auth(payload: dict[str, Any]) -> dict[str, Any]:
    init_db()

    now = current_timestamp()
    prepared = prepare_auth_payload(payload)
    prepared["created_at"] = now
    prepared["updated_at"] = now

    if not prepared.get("submitted_at"):
        prepared["submitted_at"] = now

    if has_decision(prepared) and not prepared.get("decision_at"):
        prepared["decision_at"] = now

    keys = sql_columns(
        prepared,
        set(AUTH_TABLE_COLUMNS),
        {"id"},
    )
    values = [prepared[key] for key in keys]

    with get_conn() as conn:
        cursor = conn.execute(
            insert_sql("auths", keys),
            values,
        )

        auth_id = int(cursor.lastrowid)

    created_auth = get_auth(auth_id)

    if created_auth is not None:
        create_auth_event(auth_id, initial_timeline_event_payload(created_auth))
        return get_auth(auth_id)

    return None


def list_auths() -> list[dict[str, Any]]:
    init_db()

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM auths ORDER BY auth_start_date, client_name"
        ).fetchall()

    return [auth_row_to_dict(row) for row in rows]


def get_auth(auth_id: int) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM auths WHERE id = ?", (auth_id,)).fetchone()

    if row is None:
        return None

    return auth_row_to_dict(row)


def update_auth(auth_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    init_db()

    existing_auth = get_auth(auth_id)

    if existing_auth is None:
        return None

    prepared = prepare_auth_payload(payload)
    now = current_timestamp()
    prepared["updated_at"] = now

    if not existing_auth.get("decision_at") and has_decision(prepared):
        prepared["decision_at"] = now
    elif not prepared.get("decision_at"):
        prepared.pop("decision_at", None)

    keys = sql_columns(
        prepared,
        set(AUTH_TABLE_COLUMNS),
        {"id", "created_at"},
    )

    if not keys:
        return get_auth(auth_id)

    assignments = update_assignments(keys)
    values = [prepared[key] for key in keys]

    with get_conn() as conn:
        conn.execute(
            f"UPDATE auths SET {assignments} WHERE id = ?",  # nosec
            [*values, auth_id],
        )

    updated_auth = get_auth(auth_id)

    old_status = str(existing_auth.get("status") or "").strip()
    new_status = str(updated_auth.get("status") or "").strip() if updated_auth else ""

    if old_status == "Pending" and new_status == "Approved":
        create_auth_event(
            auth_id,
            {
                "event_type": "Payer Response",
                "event_date": str(
                    updated_auth.get("decision_at") or current_timestamp()
                )[:10],
                "event_time": "",
                "outcome": "Approved",
                "notes": "Authorization marked approved.",
                "requested_days": int(updated_auth.get("requested_days") or 0),
                "approved_days": int(updated_auth.get("approved_days") or 0),
                "auth_start_date": str(updated_auth.get("auth_start_date") or ""),
                "auth_end_date": str(updated_auth.get("auth_end_date") or ""),
                "review_due_date": str(updated_auth.get("review_due_date") or ""),
            },
        )

    return get_auth(auth_id)


def delete_auth(auth_id: int) -> bool:
    init_db()

    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM auths WHERE id = ?", (auth_id,))

    return cursor.rowcount > 0
