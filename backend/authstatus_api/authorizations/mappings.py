from __future__ import annotations

from typing import Any

from authstatus_api.crypto import (
    decrypt_auth_record,
    decrypt_text,
    encrypt_auth_payload,
    encrypt_text,
)

BOOLEAN_FIELDS = {
    "care_manager_enabled",
    "discharge_clinical_needed",
    "no_pa_required",
    "progress_made",
    "facility_informed",
    "waiting_on_clinicals",
    "p2p_requested",
    "appeal_submitted",
    "retro_requested",
}

OPTIONAL_AUTH_TEXT_FIELDS = {
    "auth_start_date",
    "auth_end_date",
    "programming_days",
    "review_due_date",
    "submitted_at",
    "decision_at",
    "denial_reason_category",
    "denial_reason_notes",
    "denial_prevention_notes",
    "denial_date",
    "denial_through_date",
    "denial_level_of_care",
    "denial_source",
    "p2p_scheduled_at",
    "p2p_deadline",
    "p2p_outcome",
    "p2p_reviewer",
    "p2p_notes",
    "appeal_deadline",
    "appeal_outcome",
    "appeal_notes",
    "retro_deadline",
    "retro_outcome",
    "retro_notes",
}

OPTIONAL_EVENT_DATE_FIELDS = {
    "auth_start_date",
    "auth_end_date",
    "review_due_date",
}


def auth_row_to_dict(row: Any) -> dict[str, Any]:
    record = dict(row)
    decrypted = decrypt_auth_record(record)

    for field in BOOLEAN_FIELDS:
        if field in decrypted:
            decrypted[field] = bool(decrypted[field])

    for field in OPTIONAL_AUTH_TEXT_FIELDS:
        if decrypted.get(field) is None:
            decrypted[field] = ""

    return decrypted


def prepare_auth_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    prepared = payload.copy()

    for field in BOOLEAN_FIELDS:
        if field in prepared:
            prepared[field] = int(bool(prepared[field]))

    return encrypt_auth_payload(prepared)


def auth_event_row_to_dict(row: Any) -> dict[str, Any]:
    record = dict(row)

    if "notes" in record:
        record["notes"] = decrypt_text(record["notes"])

    for field in OPTIONAL_EVENT_DATE_FIELDS:
        if record.get(field) is None:
            record[field] = ""

    return record


def prepare_auth_event_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    prepared = payload.copy()

    if "notes" in prepared:
        prepared["notes"] = encrypt_text(prepared["notes"])

    return prepared
