from __future__ import annotations

import pytest

from authstatus_api.authorizations.decision_snapshots import (
    InvalidAuthDecisionSnapshotError,
    create_auth_decision_snapshot,
    get_auth_decision_snapshot,
    list_auth_decision_snapshots,
)
from authstatus_api.authorizations.events import (
    create_auth_event,
    list_auth_events,
)
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
    assert snapshot["loc"] == "PHP"
    assert snapshot["days_at_current_loc"] == 5
    assert snapshot["total_treatment_days"] == 9
    assert snapshot["context_derivation_version"] == 2
    assert snapshot["context_provenance"] == "loc_episode"


def test_snapshot_uses_loc_active_at_decision_instead_of_current_auth_loc():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "In Progress",
            "insurance": "Example Health",
        }
    )

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-06-01T00:00:00+00:00",
            "ended_at": "2026-06-27T00:00:00+00:00",
        },
    )

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "PHP",
            "started_at": "2026-06-27T00:00:00+00:00",
        },
    )

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": "Denied",
            "decision_at": "2026-06-21T00:00:00+00:00",
        },
    )

    assert snapshot is not None
    assert snapshot["loc"] == "RTC"
    assert snapshot["days_at_current_loc"] == 20
    assert snapshot["total_treatment_days"] == 20
    assert snapshot["context_provenance"] == "loc_episode"


def test_snapshot_uses_auth_loc_when_no_loc_episodes_exist():
    auth = _create_auth()

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": "Denied",
            "decision_at": "2026-09-10T00:00:00+00:00",
        },
    )

    assert snapshot is not None
    assert snapshot["loc"] == "PHP"
    assert snapshot["days_at_current_loc"] is None
    assert snapshot["total_treatment_days"] is None
    assert snapshot["context_derivation_version"] == 2
    assert snapshot["context_provenance"] == "auth_loc_fallback"


def test_snapshot_rejects_decision_outside_existing_loc_episodes():
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
            "started_at": "2026-09-10T00:00:00+00:00",
        },
    )

    with pytest.raises(
        InvalidAuthDecisionSnapshotError,
        match="No LOC episode is active at decision_at",
    ):
        create_auth_decision_snapshot(
            auth["id"],
            {
                "outcome": "Denied",
                "decision_at": "2026-09-07T00:00:00+00:00",
            },
        )


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

    manual_snapshots = [
        snapshot for snapshot in snapshots if snapshot["source"] == "manual"
    ]

    assert [item["outcome"] for item in manual_snapshots] == [
        "Approved",
        "Denied",
    ]


def test_create_auth_automatically_creates_denied_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Example Health",
            "requested_days": 5,
            "approved_days": 0,
            "denied_days": 5,
        }
    )

    assert auth is not None

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None
    assert len(snapshots) == 1
    assert snapshots[0]["outcome"] == "Denied"
    assert snapshots[0]["source"] == "automatic"
    assert snapshots[0]["snapshot_role"] == "root"
    assert snapshots[0]["root_snapshot_id"] == snapshots[0]["id"]
    assert snapshots[0]["parent_snapshot_id"] is None
    assert snapshots[0]["follow_up_decision_at"] is None


def test_create_auth_automatically_creates_partial_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Approved",
            "insurance": "Example Health",
            "requested_days": 5,
            "approved_days": 2,
            "denied_days": 3,
        }
    )

    assert auth is not None

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None
    assert len(snapshots) == 1
    assert snapshots[0]["outcome"] == "Partial"


def test_repeated_update_does_not_duplicate_automatic_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "In Progress",
            "insurance": "Example Health",
            "requested_days": 5,
        }
    )

    assert auth is not None

    from authstatus_api.authorizations.records import update_auth

    first = update_auth(
        auth["id"],
        {
            "status": "Denied",
            "denied_days": 5,
        },
    )

    assert first is not None

    second = update_auth(
        auth["id"],
        {
            "denial_reason_category": "Medical Necessity",
        },
    )

    assert second is not None

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None
    assert len(snapshots) == 1
    assert snapshots[0]["outcome"] == "Denied"


def test_nondecision_auth_does_not_create_automatic_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "In Progress",
            "insurance": "Example Health",
        }
    )

    assert auth is not None

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots == []


def test_p2p_outcome_creates_linked_automatic_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Example Health",
            "requested_days": 5,
            "approved_days": 0,
            "denied_days": 5,
            "decision_at": "2026-09-10T12:00:00+00:00",
        }
    )

    assert auth is not None

    from authstatus_api.authorizations.records import update_auth

    update_auth(
        auth["id"],
        {
            "p2p_requested": True,
            "p2p_scheduled_at": "2026-09-15T14:00:00+00:00",
            "p2p_deadline": "2026-09-16",
            "p2p_decided_at": "2026-09-15T16:30:00+00:00",
            "p2p_outcome": "Overturned",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None
    assert len(snapshots) == 2

    root = next(item for item in snapshots if item["snapshot_role"] == "root")
    p2p_snapshot = next(
        item for item in snapshots if item["outcome"] == "P2P Overturned"
    )

    assert p2p_snapshot["source"] == "automatic"
    assert p2p_snapshot["snapshot_role"] == "follow_up"
    assert p2p_snapshot["review_type"] == "p2p"
    assert p2p_snapshot["parent_snapshot_id"] == root["id"]
    assert p2p_snapshot["root_snapshot_id"] == root["id"]

    assert p2p_snapshot["decision_at"] == root["decision_at"]
    assert p2p_snapshot["follow_up_decision_at"] == "2026-09-15T16:30:00+00:00"

    assert p2p_snapshot["requested_days"] == root["requested_days"]
    assert p2p_snapshot["approved_days"] == root["approved_days"]
    assert p2p_snapshot["denied_days"] == root["denied_days"]

    assert p2p_snapshot["loc"] == root["loc"]
    assert p2p_snapshot["insurance"] == root["insurance"]
    assert p2p_snapshot["insurance_plan"] == root["insurance_plan"]

    assert p2p_snapshot["context_provenance"] == "inherited_root"

    events = list_auth_events(auth["id"])

    assert events is not None

    p2p_event = next(event for event in events if event["event_type"] == "Peer Review")

    assert p2p_snapshot["auth_event_id"] == p2p_event["id"]
    assert p2p_event["event_date"] == "2026-09-15"


def test_appeal_outcome_links_to_upheld_p2p_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Example Health",
            "requested_days": 5,
            "approved_days": 0,
            "denied_days": 5,
            "decision_at": "2026-09-10T12:00:00+00:00",
        }
    )

    assert auth is not None

    from authstatus_api.authorizations.records import update_auth

    update_auth(
        auth["id"],
        {
            "p2p_requested": True,
            "p2p_decided_at": "2026-09-15T12:00:00+00:00",
            "p2p_outcome": "Upheld",
        },
    )

    update_auth(
        auth["id"],
        {
            "appeal_submitted": True,
            "appeal_deadline": "2026-09-20",
            "appeal_decided_at": "2026-09-18T13:00:00+00:00",
            "appeal_outcome": "Overturned",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None

    root = next(item for item in snapshots if item["snapshot_role"] == "root")
    p2p = next(item for item in snapshots if item["outcome"] == "P2P Upheld")
    appeal = next(item for item in snapshots if item["outcome"] == "Appeal Overturned")

    assert p2p["parent_snapshot_id"] == root["id"]
    assert p2p["root_snapshot_id"] == root["id"]

    assert appeal["snapshot_role"] == "follow_up"
    assert appeal["review_type"] == "appeal"
    assert appeal["parent_snapshot_id"] == p2p["id"]
    assert appeal["root_snapshot_id"] == root["id"]

    assert appeal["decision_at"] == root["decision_at"]
    assert appeal["follow_up_decision_at"] == "2026-09-18T13:00:00+00:00"

    assert appeal["loc"] == root["loc"]
    assert appeal["requested_days"] == root["requested_days"]
    assert appeal["approved_days"] == root["approved_days"]
    assert appeal["denied_days"] == root["denied_days"]
    assert appeal["context_provenance"] == "inherited_root"


def test_final_p2p_without_decided_at_does_not_create_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Example Health",
            "requested_days": 5,
            "denied_days": 5,
            "decision_at": "2026-09-10T12:00:00+00:00",
        }
    )

    assert auth is not None

    from authstatus_api.authorizations.records import update_auth

    update_auth(
        auth["id"],
        {
            "p2p_requested": True,
            "p2p_scheduled_at": "2026-09-15T14:00:00+00:00",
            "p2p_deadline": "2026-09-16",
            "p2p_outcome": "Overturned",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None

    assert not any(item["review_type"] == "p2p" for item in snapshots)


def test_appeal_inherits_root_loc_after_auth_steps_down():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "In Progress",
            "insurance": "Example Health",
            "insurance_plan": "Gold PPO",
            "requested_days": 5,
        }
    )

    assert auth is not None

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "RTC",
            "started_at": "2026-06-01T00:00:00+00:00",
            "ended_at": "2026-06-27T00:00:00+00:00",
        },
    )

    create_auth_loc_episode(
        auth["id"],
        {
            "loc": "PHP",
            "started_at": "2026-06-27T00:00:00+00:00",
        },
    )

    from authstatus_api.authorizations.records import update_auth

    denied = update_auth(
        auth["id"],
        {
            "status": "Denied",
            "denied_days": 5,
            "decision_at": "2026-06-21T00:00:00+00:00",
        },
    )

    assert denied is not None

    stepped_down = update_auth(
        auth["id"],
        {
            "loc": "PHP",
        },
    )

    assert stepped_down is not None

    update_auth(
        auth["id"],
        {
            "appeal_submitted": True,
            "appeal_decided_at": "2026-07-12T00:00:00+00:00",
            "appeal_outcome": "Overturned",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None

    root = next(item for item in snapshots if item["snapshot_role"] == "root")
    appeal = next(item for item in snapshots if item["review_type"] == "appeal")

    assert root["loc"] == "RTC"
    assert root["days_at_current_loc"] == 20
    assert root["total_treatment_days"] == 20

    assert appeal["loc"] == "RTC"
    assert appeal["days_at_current_loc"] == 20
    assert appeal["total_treatment_days"] == 20

    assert appeal["parent_snapshot_id"] == root["id"]
    assert appeal["root_snapshot_id"] == root["id"]
    assert appeal["decision_at"] == "2026-06-21T00:00:00+00:00"
    assert appeal["follow_up_decision_at"] == "2026-07-12T00:00:00+00:00"


def test_retro_without_prior_decision_creates_root_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Retro",
            "status": "In Progress",
            "insurance": "Example Health",
            "requested_days": 10,
        }
    )

    assert auth is not None

    from authstatus_api.authorizations.records import update_auth

    update_auth(
        auth["id"],
        {
            "retro_requested": True,
            "retro_deadline": "2026-09-20",
            "retro_decided_at": "2026-09-18T15:00:00+00:00",
            "retro_outcome": "Partially Approved",
            "retro_reviewed_from": "2026-09-01",
            "retro_reviewed_to": "2026-09-10",
            "retro_reviewed_loc": "RTC",
            "retro_reason": "Authorization was not obtained before service.",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None
    assert len(snapshots) == 1

    retro_snapshot = snapshots[0]

    assert retro_snapshot["outcome"] == "Retro Partially Approved"
    assert retro_snapshot["source"] == "automatic"
    assert retro_snapshot["snapshot_role"] == "root"
    assert retro_snapshot["review_type"] == "retro"
    assert retro_snapshot["parent_snapshot_id"] is None
    assert retro_snapshot["root_snapshot_id"] == retro_snapshot["id"]
    assert retro_snapshot["follow_up_decision_at"] is None

    assert retro_snapshot["decision_at"] == "2026-09-18T15:00:00+00:00"
    assert retro_snapshot["loc"] == "RTC"

    assert retro_snapshot["reviewed_from"] == "2026-09-01"
    assert retro_snapshot["reviewed_to"] == "2026-09-10"
    assert retro_snapshot["reviewed_loc"] == "RTC"
    assert (
        retro_snapshot["retro_reason"]
        == "Authorization was not obtained before service."
    )

    assert retro_snapshot["days_at_current_loc"] is None
    assert retro_snapshot["total_treatment_days"] is None
    assert retro_snapshot["context_derivation_version"] == 2
    assert retro_snapshot["context_provenance"] == "retro_review_context"

    events = list_auth_events(auth["id"])

    assert events is not None

    retro_event = next(event for event in events if event["event_type"] == "Retro Auth")

    assert retro_snapshot["auth_event_id"] == retro_event["id"]


def test_retro_after_denial_creates_follow_up_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Example Health",
            "requested_days": 5,
            "approved_days": 0,
            "denied_days": 5,
            "decision_at": "2026-09-10T12:00:00+00:00",
        }
    )

    assert auth is not None

    from authstatus_api.authorizations.records import update_auth

    update_auth(
        auth["id"],
        {
            "retro_requested": True,
            "retro_deadline": "2026-09-25",
            "retro_decided_at": "2026-09-22T14:00:00+00:00",
            "retro_outcome": "Approved",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None
    assert len(snapshots) == 2

    root = next(item for item in snapshots if item["snapshot_role"] == "root")
    retro = next(item for item in snapshots if item["review_type"] == "retro")

    assert retro["outcome"] == "Retro Approved"
    assert retro["source"] == "automatic"
    assert retro["snapshot_role"] == "follow_up"
    assert retro["parent_snapshot_id"] == root["id"]
    assert retro["root_snapshot_id"] == root["id"]

    assert retro["decision_at"] == root["decision_at"]
    assert retro["follow_up_decision_at"] == "2026-09-22T14:00:00+00:00"

    assert retro["facility"] == root["facility"]
    assert retro["insurance"] == root["insurance"]
    assert retro["insurance_plan"] == root["insurance_plan"]
    assert retro["loc"] == root["loc"]
    assert retro["requested_days"] == root["requested_days"]
    assert retro["approved_days"] == root["approved_days"]
    assert retro["denied_days"] == root["denied_days"]

    assert retro["context_provenance"] == "inherited_root"


def test_final_retro_without_decided_at_does_not_create_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "PHP",
            "submission_methods": "Fax",
            "auth_type": "Retro",
            "status": "In Progress",
            "insurance": "Example Health",
            "requested_days": 10,
        }
    )

    assert auth is not None

    from authstatus_api.authorizations.records import update_auth

    update_auth(
        auth["id"],
        {
            "retro_requested": True,
            "retro_deadline": "2026-09-20",
            "retro_outcome": "Approved",
            "retro_reviewed_from": "2026-09-01",
            "retro_reviewed_to": "2026-09-10",
            "retro_reviewed_loc": "RTC",
            "retro_reason": "Authorization was not obtained before service.",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots is not None
    assert not any(item["review_type"] == "retro" for item in snapshots)


def test_pending_follow_up_does_not_create_decision_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "In Progress",
            "insurance": "Example Health",
        }
    )

    assert auth is not None

    from authstatus_api.authorizations.records import update_auth

    update_auth(
        auth["id"],
        {
            "p2p_requested": True,
            "p2p_scheduled_at": "2026-09-15T14:00:00+00:00",
            "p2p_outcome": "Pending",
        },
    )

    snapshots = list_auth_decision_snapshots(auth["id"])

    assert snapshots == []


def test_follow_up_snapshot_helper_creates_p2p_snapshot():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Example Health",
            "requested_days": 5,
            "denied_days": 5,
            "decision_at": "2026-09-10T12:00:00+00:00",
        }
    )

    assert auth is not None

    auth["p2p_outcome"] = "Overturned"
    auth["p2p_decided_at"] = "2026-09-15T14:00:00+00:00"

    from authstatus_api.authorizations.decision_snapshots import (
        create_automatic_follow_up_decision_snapshots,
    )

    created = create_automatic_follow_up_decision_snapshots(auth)

    assert len(created) == 1
    assert created[0]["outcome"] == "P2P Overturned"
    assert created[0]["source"] == "automatic"
    assert created[0]["snapshot_role"] == "follow_up"
    assert created[0]["review_type"] == "p2p"
    assert created[0]["follow_up_decision_at"] == "2026-09-15T14:00:00+00:00"
