from __future__ import annotations

from typing import Any

from authstatus_api.authorizations.events import (
    create_auth_event,
    list_auth_events,
    update_auth_event,
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
    "auth_number",
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
    "denial_reason_category",
    "denial_reason_notes",
    "denial_prevention_notes",
    "denied_days",
    "denial_date",
    "denial_through_date",
    "denial_level_of_care",
    "denial_source",
    "p2p_requested",
    "p2p_scheduled_at",
    "p2p_deadline",
    "p2p_outcome",
    "p2p_reviewer",
    "p2p_notes",
    "appeal_submitted",
    "appeal_deadline",
    "appeal_outcome",
    "appeal_notes",
    "retro_requested",
    "retro_deadline",
    "retro_outcome",
    "retro_notes",
    "created_at",
    "updated_at",
}


DENIAL_TIMELINE_EVENT_TYPE = "Payer Response"
DENIAL_TIMELINE_OUTCOME = "Denied"

DENIAL_TIMELINE_FIELDS = {
    "status",
    "denial_reason_category",
    "denial_reason_notes",
    "denial_date",
    "denial_through_date",
    "denial_level_of_care",
    "denial_source",
}


def _should_sync_denial_timeline_event(
    payload: dict[str, Any],
    updated_auth: dict[str, Any],
) -> bool:
    if not DENIAL_TIMELINE_FIELDS.intersection(payload):
        return False

    status = str(updated_auth.get("status") or "").strip()
    reason = str(updated_auth.get("denial_reason_category") or "").strip()
    denial_date = str(updated_auth.get("denial_date") or "").strip()

    return status == "Denied" or bool(reason) or bool(denial_date)


def _denial_timeline_notes(auth_record: dict[str, Any]) -> str:
    notes = ["Denial details recorded."]

    reason = str(auth_record.get("denial_reason_category") or "").strip()
    source = str(auth_record.get("denial_source") or "").strip()
    level_of_care = str(auth_record.get("denial_level_of_care") or "").strip()
    denied_through = str(auth_record.get("denial_through_date") or "").strip()
    reason_notes = str(auth_record.get("denial_reason_notes") or "").strip()

    if reason:
        notes.append(f"Reason category: {reason}.")

    if source:
        notes.append(f"Source: {source}.")

    if level_of_care:
        notes.append(f"Denied LOC: {level_of_care}.")

    if denied_through:
        notes.append(f"Denied through: {denied_through}.")

    if reason_notes:
        notes.append(f"Reason notes: {reason_notes}")

    return " ".join(notes)


def _denial_timeline_payload(
    auth_record: dict[str, Any],
) -> dict[str, Any]:
    event_date = str(auth_record.get("denial_date") or "").strip()

    if not event_date:
        event_date = str(auth_record.get("decision_at") or current_timestamp())[:10]

    return {
        "event_type": DENIAL_TIMELINE_EVENT_TYPE,
        "event_date": event_date,
        "event_time": "",
        "outcome": DENIAL_TIMELINE_OUTCOME,
        "notes": _denial_timeline_notes(auth_record),
        "requested_days": 0,
        "approved_days": 0,
        "auth_start_date": "",
        "auth_end_date": "",
        "review_due_date": "",
    }


def _sync_denial_timeline_event(auth_id: int, auth_record: dict[str, Any]) -> None:
    events = list_auth_events(auth_id)

    if events is None:
        return

    payload = _denial_timeline_payload(auth_record)

    existing_event = next(
        (
            event
            for event in events
            if event["event_type"] == DENIAL_TIMELINE_EVENT_TYPE
            and event["outcome"] == DENIAL_TIMELINE_OUTCOME
        ),
        None,
    )

    if existing_event is None:
        create_auth_event(auth_id, payload)
        return

    update_auth_event(auth_id, existing_event["id"], payload)


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

    if _should_sync_denial_timeline_event(payload, updated_auth):
        _sync_denial_timeline_event(auth_id, updated_auth)

    return get_auth(auth_id)


def delete_auth(auth_id: int) -> bool:
    init_db()

    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM auths WHERE id = ?", (auth_id,))

    return cursor.rowcount > 0
