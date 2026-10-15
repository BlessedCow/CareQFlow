from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from authstatus_api.schemas import (
    AuthCreate,
    AuthEventCreate,
    AuthEventUpdate,
    AuthUpdate,
)


def valid_auth_payload() -> dict:
    return {
        "facility": "Example Facility",
        "client_name": "Example Patient",
        "loc": "PHP",
        "submission_methods": "Portal",
        "auth_type": "Initial",
        "status": "Pending",
    }


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("date_of_birth", "01/15/1990"),
        ("date_of_birth", "1990-02-30"),
        ("auth_start_date", "2026/06/25"),
        ("auth_end_date", "June 30, 2026"),
        ("review_due_date", "2026-13-01"),
    ],
)
def test_auth_create_rejects_invalid_date_values(
    field_name,
    value,
):
    payload = valid_auth_payload()
    payload[field_name] = value

    with pytest.raises(
        ValidationError,
        match="YYYY-MM-DD",
    ):
        AuthCreate.model_validate(payload)


def test_auth_create_trims_valid_dates():
    payload = valid_auth_payload()
    payload.update(
        {
            "date_of_birth": " 1990-01-15 ",
            "auth_start_date": " 2026-06-25 ",
            "auth_end_date": " 2026-06-30 ",
            "review_due_date": " 2026-07-01 ",
        }
    )

    auth = AuthCreate.model_validate(payload)

    assert auth.date_of_birth == "1990-01-15"
    assert auth.auth_start_date == "2026-06-25"
    assert auth.auth_end_date == "2026-06-30"
    assert auth.review_due_date == "2026-07-01"


def test_auth_create_rejects_future_date_of_birth():
    payload = valid_auth_payload()
    payload["date_of_birth"] = (date.today() + timedelta(days=1)).isoformat()

    with pytest.raises(
        ValidationError,
        match="Date of birth cannot be in the future",
    ):
        AuthCreate.model_validate(payload)


def test_auth_create_rejects_end_date_before_start_date():
    payload = valid_auth_payload()
    payload.update(
        {
            "auth_start_date": "2026-06-30",
            "auth_end_date": "2026-06-25",
        }
    )

    with pytest.raises(
        ValidationError,
        match="end date cannot be before",
    ):
        AuthCreate.model_validate(payload)


def test_auth_update_validates_dates_when_both_are_present():
    with pytest.raises(
        ValidationError,
        match="end date cannot be before",
    ):
        AuthUpdate.model_validate(
            {
                "auth_start_date": "2026-06-30",
                "auth_end_date": "2026-06-25",
            }
        )


def test_auth_update_allows_single_date_in_partial_update():
    update = AuthUpdate.model_validate(
        {
            "auth_end_date": "2026-06-30",
        }
    )

    assert update.auth_end_date == "2026-06-30"


def test_auth_event_create_rejects_invalid_event_date():
    with pytest.raises(
        ValidationError,
        match="YYYY-MM-DD",
    ):
        AuthEventCreate.model_validate(
            {
                "event_type": "Concurrent Review",
                "event_date": "06/25/2026",
            }
        )


def test_auth_event_create_rejects_reversed_date_range():
    with pytest.raises(
        ValidationError,
        match="end date cannot be before",
    ):
        AuthEventCreate.model_validate(
            {
                "event_type": "Concurrent Review",
                "event_date": "2026-06-25",
                "auth_start_date": "2026-06-30",
                "auth_end_date": "2026-06-25",
            }
        )


def test_auth_event_update_allows_partial_date_update():
    update = AuthEventUpdate.model_validate(
        {
            "review_due_date": "2026-07-01",
        }
    )

    assert update.review_due_date == "2026-07-01"


@pytest.mark.parametrize(
    "field_name",
    [
        "p2p_decided_at",
        "appeal_decided_at",
        "retro_decided_at",
    ],
)
def test_auth_create_validates_follow_up_decision_dates(field_name):
    payload = valid_auth_payload()
    payload[field_name] = "07/12/2026"

    with pytest.raises(ValidationError, match="YYYY-MM-DD"):
        AuthCreate.model_validate(payload)


def test_auth_update_accepts_follow_up_decision_dates():
    update = AuthUpdate.model_validate(
        {
            "p2p_decided_at": "2026-07-01",
            "appeal_decided_at": "2026-07-12",
            "retro_decided_at": "2026-07-20",
        }
    )

    assert update.p2p_decided_at == "2026-07-01"
    assert update.appeal_decided_at == "2026-07-12"
    assert update.retro_decided_at == "2026-07-20"


@pytest.mark.parametrize(
    "field_name",
    [
        "retro_reviewed_from",
        "retro_reviewed_to",
    ],
)
def test_auth_create_validates_retro_review_dates(field_name):
    payload = valid_auth_payload()
    payload[field_name] = "07/12/2026"

    with pytest.raises(ValidationError, match="YYYY-MM-DD"):
        AuthCreate.model_validate(payload)


def test_auth_update_accepts_retro_review_context():
    update = AuthUpdate.model_validate(
        {
            "retro_reviewed_from": "2026-06-01",
            "retro_reviewed_to": "2026-06-10",
            "retro_reviewed_loc": "RTC",
            "retro_reason": "Authorization not obtained before service.",
        }
    )

    assert update.retro_reviewed_from == "2026-06-01"
    assert update.retro_reviewed_to == "2026-06-10"
    assert update.retro_reviewed_loc == "RTC"
    assert update.retro_reason == "Authorization not obtained before service."
