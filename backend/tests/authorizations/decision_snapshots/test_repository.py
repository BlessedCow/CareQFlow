from __future__ import annotations

import pytest

from authstatus_api.authorizations.decision_snapshots import (
    InvalidAuthDecisionSnapshotError,
    create_auth_decision_snapshot,
    get_auth_decision_snapshot,
    list_auth_decision_snapshots,
)
from authstatus_api.authorizations.events import create_auth_event
from authstatus_api.authorizations.loc_episodes import create_auth_loc_episode
from authstatus_api.authorizations.records import create_auth
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", generate_encryption_key())
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def _create_auth() -> dict:
    record = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Example Health",
            "insurance_plan": "Gold PPO",
            "requested_days": 5,
            "approved_days": 2,
            "denied_days": 3,
            "denial_reason_category": "Medical Necessity",
            "denial_source": "Payer Letter",
        }
    )

    assert record is not None
    return record


def test_create_auth_decision_snapshot_uses_current_auth_values():
    auth = _create_auth()

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": "Partial",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
    )

    assert snapshot is not None
    assert snapshot["facility"] == "Facility A"
    assert snapshot["insurance"] == "Example Health"
    assert snapshot["insurance_plan"] == "Gold PPO"
    assert snapshot["loc"] == "PHP"
    assert snapshot["auth_type"] == "Concurrent"
    assert snapshot["outcome"] == "Partial"
    assert snapshot["requested_days"] == 5
    assert snapshot["approved_days"] == 2
    assert snapshot["denied_days"] == 3
    assert snapshot["denial_reason_category"] == "Medical Necessity"
    assert snapshot["denial_source"] == "Payer Letter"


def test_create_auth_decision_snapshot_derives_loc_context():
    auth = _create_auth()

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-09-01T00:00:00+00:00",
            "ended_at": "2026-09-05T00:00:00+00:00",
        },
    )

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "PHP",
            "started_at": "2026-09-05T00:00:00+00:00",
        },
    )

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": "Denied",
            "decision_at": "2026-09-10T00:00:00+00:00",
        },
    )

    assert snapshot is not None
    assert snapshot["days_at_current_loc"] == 5
    assert snapshot["total_treatment_days"] == 9


def test_snapshot_values_remain_frozen_after_auth_changes():
    auth = _create_auth()

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": "Denied",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
    )

    assert snapshot is not None

    from authstatus_api.authorizations.records import update_auth

    updated = update_auth(
        auth["id"],
        {
            "insurance": "Different Health",
            "insurance_plan": "Different Plan",
            "loc": "IOP",
        },
    )

    assert updated is not None

    stored = get_auth_decision_snapshot(
        auth["id"],
        snapshot["id"],
    )

    assert stored is not None
    assert stored["insurance"] == "Example Health"
    assert stored["insurance_plan"] == "Gold PPO"
    assert stored["loc"] == "PHP"


def test_snapshot_can_link_auth_event():
    auth = _create_auth()

    event = create_auth_event(
        auth["id"],
        {
            "event_type": "Concurrent Review",
            "event_date": "2026-09-10",
        },
    )

    assert event is not None

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "auth_event_id": event["id"],
            "outcome": "Approved",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
    )

    assert snapshot is not None
    assert snapshot["auth_event_id"] == event["id"]


def test_snapshot_rejects_event_from_another_auth():
    first_auth = _create_auth()
    second_auth = _create_auth()

    event = create_auth_event(
        second_auth["id"],
        {
            "event_type": "Concurrent Review",
            "event_date": "2026-09-10",
        },
    )

    assert event is not None

    with pytest.raises(
        InvalidAuthDecisionSnapshotError,
        match="auth_event_id must reference an event for this authorization",
    ):
        create_auth_decision_snapshot(
            first_auth["id"],
            {
                "auth_event_id": event["id"],
                "outcome": "Denied",
                "decision_at": "2026-09-10T12:00:00+00:00",
            },
        )


def test_snapshot_rejects_invalid_decision_timestamp():
    auth = _create_auth()

    with pytest.raises(
        InvalidAuthDecisionSnapshotError,
        match="decision_at must be a valid ISO 8601 timestamp",
    ):
        create_auth_decision_snapshot(
            auth["id"],
            {
                "outcome": "Denied",
                "decision_at": "not-a-timestamp",
            },
        )


def test_list_auth_decision_snapshots_is_chronological():
    auth = _create_auth()

    create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": "Denied",
            "decision_at": "2026-09-12T12:00:00+00:00",
        },
    )

    create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": "Approved",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None
    assert [item["outcome"] for item in snapshots] == [
        "Approved",
        "Denied",
    ]
