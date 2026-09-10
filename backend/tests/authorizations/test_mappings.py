from __future__ import annotations

import pytest

from authstatus_api.authorizations.mappings import (
    auth_event_row_to_dict,
    auth_row_to_dict,
    prepare_auth_event_payload,
    prepare_auth_payload,
)
from authstatus_api.crypto import (
    decrypt_text,
    generate_encryption_key,
)
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_encryption_key(monkeypatch):
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_prepare_auth_payload_converts_boolean_fields():
    prepared = prepare_auth_payload(
        {
            "client_name": "Example Patient",
            "care_manager_enabled": True,
            "no_pa_required": False,
        }
    )

    assert prepared["care_manager_enabled"] == 1
    assert prepared["no_pa_required"] == 0


def test_auth_row_to_dict_restores_boolean_fields():
    record = auth_row_to_dict(
        {
            "id": 1,
            "client_name": "Example Patient",
            "care_manager_enabled": 1,
            "no_pa_required": 0,
        }
    )

    assert record["care_manager_enabled"] is True
    assert record["no_pa_required"] is False


def test_auth_row_to_dict_normalizes_nullable_insurance_plan():
    record = auth_row_to_dict(
        {
            "id": 1,
            "client_name": "Example Patient",
            "insurance_plan": None,
        }
    )

    assert record["insurance_plan"] == ""


def test_auth_row_to_dict_normalizes_nullable_dates():
    record = auth_row_to_dict(
        {
            "id": 1,
            "client_name": "Example Patient",
            "auth_start_date": None,
            "auth_end_date": None,
            "review_due_date": None,
            "submitted_at": None,
            "decision_at": None,
        }
    )

    assert record["auth_start_date"] == ""
    assert record["auth_end_date"] == ""
    assert record["review_due_date"] == ""
    assert record["submitted_at"] == ""
    assert record["decision_at"] == ""


def test_prepare_auth_event_payload_encrypts_notes():
    prepared = prepare_auth_event_payload(
        {
            "event_type": "Payer Response",
            "notes": "Sensitive event note",
        }
    )

    assert prepared["notes"] != "Sensitive event note"
    assert decrypt_text(prepared["notes"]) == ("Sensitive event note")


def test_auth_event_row_to_dict_decrypts_notes():
    prepared = prepare_auth_event_payload(
        {
            "notes": "Sensitive event note",
        }
    )

    record = auth_event_row_to_dict(
        {
            "id": 1,
            "auth_id": 2,
            "notes": prepared["notes"],
        }
    )

    assert record["notes"] == "Sensitive event note"


def test_auth_event_row_to_dict_normalizes_nullable_dates():
    record = auth_event_row_to_dict(
        {
            "id": 1,
            "auth_id": 2,
            "notes": "",
            "auth_start_date": None,
            "auth_end_date": None,
            "review_due_date": None,
        }
    )

    assert record["auth_start_date"] == ""
    assert record["auth_end_date"] == ""
    assert record["review_due_date"] == ""
