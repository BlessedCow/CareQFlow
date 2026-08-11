from __future__ import annotations

from typing import Any

from authstatus_api.authorizations.events import (
    create_auth_event,
    delete_auth_event,
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

P2P_TIMELINE_EVENT_TYPE = "Peer Review"
APPEAL_TIMELINE_EVENT_TYPE = "Appeal"
RETRO_TIMELINE_EVENT_TYPE = "Retro Auth"

DENIAL_TIMELINE_FIELDS = {
    "status",
    "denial_reason_category",
    "denial_reason_notes",
    "denial_date",
    "denial_through_date",
    "denial_level_of_care",
    "denial_source",
}

P2P_TIMELINE_FIELDS = {
    "p2p_requested",
    "p2p_scheduled_at",
    "p2p_deadline",
    "p2p_outcome",
    "p2p_reviewer",
    "p2p_notes",
}

APPEAL_TIMELINE_FIELDS = {
    "appeal_submitted",
    "appeal_deadline",
    "appeal_outcome",
    "appeal_notes",
}

RETRO_TIMELINE_FIELDS = {
    "retro_requested",
    "retro_deadline",
    "retro_outcome",
    "retro_notes",
}


def _has_denial_details(auth_record: dict[str, Any]) -> bool:
    status = str(auth_record.get("status") or "").strip()
    reason = str(auth_record.get("denial_reason_category") or "").strip()
    denial_date = str(auth_record.get("denial_date") or "").strip()
    denied_through = str(auth_record.get("denial_through_date") or "").strip()
    level_of_care = str(auth_record.get("denial_level_of_care") or "").strip()
    source = str(auth_record.get("denial_source") or "").strip()
    reason_notes = str(auth_record.get("denial_reason_notes") or "").strip()

    return any(
        (
            status == "Denied",
            bool(reason),
            bool(denial_date),
            bool(denied_through),
            bool(level_of_care),
            bool(source),
            bool(reason_notes),
        )
    )


def _should_sync_denial_timeline_event(
    payload: dict[str, Any],
    updated_auth: dict[str, Any],
) -> bool:
    return bool(DENIAL_TIMELINE_FIELDS.intersection(payload))


def _has_p2p_details(auth_record: dict[str, Any]) -> bool:
    return (
        bool(auth_record.get("p2p_requested"))
        or bool(str(auth_record.get("p2p_scheduled_at") or "").strip())
        or bool(str(auth_record.get("p2p_deadline") or "").strip())
        or bool(str(auth_record.get("p2p_outcome") or "").strip())
        or bool(str(auth_record.get("p2p_reviewer") or "").strip())
        or bool(str(auth_record.get("p2p_notes") or "").strip())
    )


def _should_sync_p2p_timeline_event(
    payload: dict[str, Any],
    updated_auth: dict[str, Any],
) -> bool:
    return bool(P2P_TIMELINE_FIELDS.intersection(payload))


def _has_appeal_details(auth_record: dict[str, Any]) -> bool:
    return (
        bool(auth_record.get("appeal_submitted"))
        or bool(str(auth_record.get("appeal_deadline") or "").strip())
        or bool(str(auth_record.get("appeal_outcome") or "").strip())
        or bool(str(auth_record.get("appeal_notes") or "").strip())
    )


def _should_sync_appeal_timeline_event(
    payload: dict[str, Any],
    updated_auth: dict[str, Any],
) -> bool:
    return bool(APPEAL_TIMELINE_FIELDS.intersection(payload))


def _has_retro_details(auth_record: dict[str, Any]) -> bool:
    return (
        bool(auth_record.get("retro_requested"))
        or bool(str(auth_record.get("retro_deadline") or "").strip())
        or bool(str(auth_record.get("retro_outcome") or "").strip())
        or bool(str(auth_record.get("retro_notes") or "").strip())
    )


def _should_sync_retro_timeline_event(
    payload: dict[str, Any],
    updated_auth: dict[str, Any],
) -> bool:
    return bool(RETRO_TIMELINE_FIELDS.intersection(payload))


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


def _p2p_timeline_notes(auth_record: dict[str, Any]) -> str:
    notes = ["P2P details recorded."]

    scheduled_at = str(auth_record.get("p2p_scheduled_at") or "").strip()
    deadline = str(auth_record.get("p2p_deadline") or "").strip()
    reviewer = str(auth_record.get("p2p_reviewer") or "").strip()
    p2p_notes = str(auth_record.get("p2p_notes") or "").strip()

    if scheduled_at:
        notes.append(f"Scheduled at: {scheduled_at}.")

    if deadline:
        notes.append(f"Deadline: {deadline}.")

    if reviewer:
        notes.append(f"Reviewer: {reviewer}.")

    if p2p_notes:
        notes.append(f"Notes: {p2p_notes}")

    return " ".join(notes)


def _appeal_timeline_notes(auth_record: dict[str, Any]) -> str:
    notes = ["Appeal details recorded."]

    deadline = str(auth_record.get("appeal_deadline") or "").strip()
    appeal_notes = str(auth_record.get("appeal_notes") or "").strip()

    if deadline:
        notes.append(f"Deadline: {deadline}.")

    if appeal_notes:
        notes.append(f"Notes: {appeal_notes}")

    return " ".join(notes)


def _retro_timeline_notes(auth_record: dict[str, Any]) -> str:
    notes = ["Retro auth details recorded."]

    deadline = str(auth_record.get("retro_deadline") or "").strip()
    retro_notes = str(auth_record.get("retro_notes") or "").strip()

    if deadline:
        notes.append(f"Deadline: {deadline}.")

    if retro_notes:
        notes.append(f"Notes: {retro_notes}")

    return " ".join(notes)


def _timeline_date_from(
    auth_record: dict[str, Any],
    *field_names: str,
) -> str:
    for field_name in field_names:
        value = str(auth_record.get(field_name) or "").strip()

        if value:
            return value[:10]

    return str(auth_record.get("decision_at") or current_timestamp())[:10]


def _denial_timeline_payload(
    auth_record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_type": DENIAL_TIMELINE_EVENT_TYPE,
        "event_date": _timeline_date_from(
            auth_record,
            "denial_date",
        ),
        "event_time": "",
        "outcome": DENIAL_TIMELINE_OUTCOME,
        "notes": _denial_timeline_notes(auth_record),
        "requested_days": 0,
        "approved_days": 0,
        "auth_start_date": "",
        "auth_end_date": "",
        "review_due_date": "",
    }


def _p2p_timeline_payload(
    auth_record: dict[str, Any],
) -> dict[str, Any]:
    outcome = str(auth_record.get("p2p_outcome") or "").strip()

    return {
        "event_type": P2P_TIMELINE_EVENT_TYPE,
        "event_date": _timeline_date_from(
            auth_record,
            "p2p_deadline",
            "p2p_scheduled_at",
        ),
        "event_time": "",
        "outcome": outcome or "Pending",
        "notes": _p2p_timeline_notes(auth_record),
        "requested_days": 0,
        "approved_days": 0,
        "auth_start_date": "",
        "auth_end_date": "",
        "review_due_date": str(auth_record.get("p2p_deadline") or ""),
    }


def _appeal_timeline_payload(
    auth_record: dict[str, Any],
) -> dict[str, Any]:
    outcome = str(auth_record.get("appeal_outcome") or "").strip()

    return {
        "event_type": APPEAL_TIMELINE_EVENT_TYPE,
        "event_date": _timeline_date_from(
            auth_record,
            "appeal_deadline",
        ),
        "event_time": "",
        "outcome": outcome or "Pending",
        "notes": _appeal_timeline_notes(auth_record),
        "requested_days": 0,
        "approved_days": 0,
        "auth_start_date": "",
        "auth_end_date": "",
        "review_due_date": str(auth_record.get("appeal_deadline") or ""),
    }


def _retro_timeline_payload(
    auth_record: dict[str, Any],
) -> dict[str, Any]:
    outcome = str(auth_record.get("retro_outcome") or "").strip()

    return {
        "event_type": RETRO_TIMELINE_EVENT_TYPE,
        "event_date": _timeline_date_from(
            auth_record,
            "retro_deadline",
        ),
        "event_time": "",
        "outcome": outcome or "Pending",
        "notes": _retro_timeline_notes(auth_record),
        "requested_days": 0,
        "approved_days": 0,
        "auth_start_date": "",
        "auth_end_date": "",
        "review_due_date": str(auth_record.get("retro_deadline") or ""),
    }


def _sync_single_timeline_event(
    auth_id: int,
    event_type: str,
    event_payload: dict[str, Any] | None,
    event_outcome: str | None = None,
) -> None:
    events = list_auth_events(auth_id)

    if events is None:
        return

    existing_event = next(
        (
            event
            for event in events
            if event["event_type"] == event_type
            and (
                event_outcome is None
                or str(event.get("outcome") or "") == event_outcome
            )
        ),
        None,
    )

    if event_payload is None:
        if existing_event is not None:
            delete_auth_event(auth_id, existing_event["id"])
        return

    if existing_event is None:
        create_auth_event(auth_id, event_payload)
        return

    update_auth_event(auth_id, existing_event["id"], event_payload)


def _sync_denial_timeline_event(auth_id: int, auth_record: dict[str, Any]) -> None:
    _sync_single_timeline_event(
        auth_id,
        DENIAL_TIMELINE_EVENT_TYPE,
        (
            _denial_timeline_payload(auth_record)
            if _has_denial_details(auth_record)
            else None
        ),
        DENIAL_TIMELINE_OUTCOME,
    )


def _sync_p2p_timeline_event(auth_id: int, auth_record: dict[str, Any]) -> None:
    _sync_single_timeline_event(
        auth_id,
        P2P_TIMELINE_EVENT_TYPE,
        _p2p_timeline_payload(auth_record) if _has_p2p_details(auth_record) else None,
    )


def _sync_appeal_timeline_event(auth_id: int, auth_record: dict[str, Any]) -> None:
    _sync_single_timeline_event(
        auth_id,
        APPEAL_TIMELINE_EVENT_TYPE,
        (
            _appeal_timeline_payload(auth_record)
            if _has_appeal_details(auth_record)
            else None
        ),
    )


def _sync_retro_timeline_event(auth_id: int, auth_record: dict[str, Any]) -> None:
    _sync_single_timeline_event(
        auth_id,
        RETRO_TIMELINE_EVENT_TYPE,
        (
            _retro_timeline_payload(auth_record)
            if _has_retro_details(auth_record)
            else None
        ),
    )


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
    requested_status = str(payload.get("status") or "").strip()

    if old_status != "Approved" and requested_status == "Approved":
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

    if _should_sync_p2p_timeline_event(payload, updated_auth):
        _sync_p2p_timeline_event(auth_id, updated_auth)

    if _should_sync_appeal_timeline_event(payload, updated_auth):
        _sync_appeal_timeline_event(auth_id, updated_auth)

    if _should_sync_retro_timeline_event(payload, updated_auth):
        _sync_retro_timeline_event(auth_id, updated_auth)

    return get_auth(auth_id)


def delete_auth(auth_id: int) -> bool:
    init_db()

    with get_conn() as conn:
        cursor = conn.execute("DELETE FROM auths WHERE id = ?", (auth_id,))

    return cursor.rowcount > 0
