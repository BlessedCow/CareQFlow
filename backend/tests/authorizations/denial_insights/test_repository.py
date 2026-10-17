from __future__ import annotations

import pytest

from authstatus_api.authorizations.decision_snapshots import (
    create_auth_decision_snapshot,
)
from authstatus_api.authorizations.denial_insights.repository import (
    InvalidDenialInsightsFilterError,
    build_denial_insights,
    list_decision_snapshots,
    list_retro_root_snapshots,
)
from authstatus_api.authorizations.records import (
    create_auth,
    update_auth,
)
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


def _create_auth(
    *,
    insurance: str,
    insurance_plan: str,
    loc: str,
) -> dict:
    record = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": loc,
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Pending",
            "insurance": insurance,
            "insurance_plan": insurance_plan,
        }
    )

    assert record is not None
    return record


def _create_snapshot(
    *,
    insurance: str,
    insurance_plan: str,
    loc: str,
    outcome: str,
    decision_at: str,
) -> dict:
    auth = _create_auth(
        insurance=insurance,
        insurance_plan=insurance_plan,
        loc=loc,
    )

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "facility": "Facility A",
            "insurance": insurance,
            "insurance_plan": insurance_plan,
            "loc": loc,
            "auth_type": "Concurrent",
            "outcome": outcome,
            "decision_at": decision_at,
        },
    )

    assert snapshot is not None
    return snapshot


def test_list_decision_snapshots_filters_by_date():
    _create_snapshot(
        insurance="Payer A",
        insurance_plan="Gold",
        loc="RTC",
        outcome="Approved",
        decision_at="2026-09-01T12:00:00+00:00",
    )

    _create_snapshot(
        insurance="Payer A",
        insurance_plan="Gold",
        loc="RTC",
        outcome="Denied",
        decision_at="2026-09-10T12:00:00+00:00",
    )

    records = list_decision_snapshots(
        start_at="2026-09-05T00:00:00+00:00",
        end_at="2026-09-15T00:00:00+00:00",
    )

    assert len(records) == 1
    assert records[0]["outcome"] == "Denied"


def test_list_decision_snapshots_filters_by_dimension():
    _create_snapshot(
        insurance="Payer A",
        insurance_plan="Gold",
        loc="RTC",
        outcome="Approved",
        decision_at="2026-09-01T12:00:00+00:00",
    )

    _create_snapshot(
        insurance="Payer B",
        insurance_plan="Silver",
        loc="PHP",
        outcome="Denied",
        decision_at="2026-09-02T12:00:00+00:00",
    )

    records = list_decision_snapshots(
        filters={
            "insurance": "payer b",
            "loc": "php",
        },
    )

    assert len(records) == 1
    assert records[0]["insurance"] == "Payer B"


def test_list_decision_snapshots_excludes_follow_up_snapshots():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Payer A",
            "insurance_plan": "Gold",
            "requested_days": 5,
            "approved_days": 0,
            "denied_days": 5,
            "decision_at": "2026-09-01T12:00:00+00:00",
        }
    )

    assert auth is not None

    updated = update_auth(
        auth["id"],
        {
            "p2p_requested": True,
            "p2p_decided_at": "2026-09-03T12:00:00+00:00",
            "p2p_outcome": "Overturned",
        },
    )

    assert updated is not None

    records = list_decision_snapshots()

    assert len(records) == 1
    assert records[0]["outcome"] == "Denied"


def test_list_decision_snapshots_excludes_retro_roots():
    auth = _create_auth(
        insurance="Payer A",
        insurance_plan="Gold",
        loc="RTC",
    )

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "facility": "Facility A",
            "insurance": "Payer A",
            "insurance_plan": "Gold",
            "loc": "RTC",
            "auth_type": "Retro",
            "outcome": "Retro Approved",
            "decision_at": "2026-09-10T12:00:00+00:00",
            "snapshot_role": "root",
            "review_type": "retro",
        },
    )

    assert snapshot is not None

    records = list_decision_snapshots()

    assert records == []


def test_list_retro_root_snapshots_contains_only_retro_roots():
    retro_auth = _create_auth(
        insurance="Payer A",
        insurance_plan="Gold",
        loc="RTC",
    )

    retro_snapshot = create_auth_decision_snapshot(
        retro_auth["id"],
        {
            "facility": "Facility A",
            "insurance": "Payer A",
            "insurance_plan": "Gold",
            "loc": "RTC",
            "auth_type": "Retro",
            "outcome": "Retro Approved",
            "decision_at": "2026-09-10T12:00:00+00:00",
            "snapshot_role": "root",
            "review_type": "retro",
        },
    )

    assert retro_snapshot is not None

    clinical_snapshot = _create_snapshot(
        insurance="Payer A",
        insurance_plan="Gold",
        loc="RTC",
        outcome="Denied",
        decision_at="2026-09-11T12:00:00+00:00",
    )

    assert clinical_snapshot is not None

    records = list_retro_root_snapshots()

    assert len(records) == 1
    assert records[0]["id"] == retro_snapshot["id"]
    assert records[0]["review_type"] == "retro"
    assert records[0]["snapshot_role"] == "root"


def test_build_denial_insights_reports_standalone_retro_metrics():
    outcomes = (
        "Approved",
        "Partially Approved",
        "Denied",
    )

    for index, outcome in enumerate(
        outcomes,
        start=1,
    ):
        auth = create_auth(
            {
                "facility": "Facility A",
                "client_name": f"Retro Client {index}",
                "loc": "PHP",
                "submission_methods": "Fax",
                "auth_type": "Retro",
                "status": "In Progress",
                "insurance": "Payer A",
                "requested_days": 5,
            }
        )

        assert auth is not None

        updated = update_auth(
            auth["id"],
            {
                "retro_requested": True,
                "retro_decided_at": (f"2026-09-{10 + index:02d}T12:00:00+00:00"),
                "retro_outcome": outcome,
                "retro_reviewed_from": "2026-09-01",
                "retro_reviewed_to": "2026-09-05",
                "retro_reviewed_loc": "PHP",
                "retro_reason": ("Authorization was not obtained before service."),
            },
        )

        assert updated is not None

    result = build_denial_insights(
        dimensions=["insurance"],
    )

    retro = result["retro_root_metrics"]

    assert retro["decision_count"] == 3
    assert retro["approved_count"] == 1
    assert retro["partial_count"] == 1
    assert retro["denied_count"] == 1
    assert retro["adverse_count"] == 2

    assert retro["observed_denial_rate"] == pytest.approx(
        1 / 3,
        abs=0.0001,
    )
    assert retro["observed_partial_rate"] == pytest.approx(
        1 / 3,
        abs=0.0001,
    )

    assert result["summary"]["decision_count"] == 0


def test_list_decision_snapshots_preserves_legacy_snapshots():
    auth = _create_auth(
        insurance="Payer A",
        insurance_plan="Gold",
        loc="RTC",
    )

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "facility": "Facility A",
            "insurance": "Payer A",
            "insurance_plan": "Gold",
            "loc": "RTC",
            "auth_type": "Concurrent",
            "outcome": "Denied",
            "decision_at": "2026-09-10T12:00:00+00:00",
            "snapshot_role": "legacy",
            "review_type": "unknown",
        },
    )

    assert snapshot is not None

    records = list_decision_snapshots()

    assert len(records) == 1
    assert records[0]["id"] == snapshot["id"]
    assert records[0]["outcome"] == "Denied"


def test_list_decision_snapshots_rejects_invalid_filter():
    with pytest.raises(
        InvalidDenialInsightsFilterError,
        match="Unsupported analytics filter",
    ):
        list_decision_snapshots(
            filters={
                "client_name": "Test Client",
            },
        )


def test_list_decision_snapshots_rejects_invalid_date_range():
    with pytest.raises(
        InvalidDenialInsightsFilterError,
        match="end_at cannot be earlier than start_at",
    ):
        list_decision_snapshots(
            start_at="2026-09-10T00:00:00+00:00",
            end_at="2026-09-01T00:00:00+00:00",
        )


def test_build_denial_insights_groups_and_compares_baseline():
    for index in range(10):
        _create_snapshot(
            insurance="Payer A",
            insurance_plan="Gold",
            loc="RTC",
            outcome=("Denied" if index < 5 else "Approved"),
            decision_at=(f"2026-09-{index + 1:02d}" "T12:00:00+00:00"),
        )

    for index in range(10):
        _create_snapshot(
            insurance="Payer B",
            insurance_plan="Silver",
            loc="RTC",
            outcome=("Denied" if index < 2 else "Approved"),
            decision_at=(f"2026-08-{index + 1:02d}" "T12:00:00+00:00"),
        )

    result = build_denial_insights(
        dimensions=[
            "insurance",
        ],
        filters={
            "loc": "RTC",
        },
        baseline_filters={
            "loc": "RTC",
        },
    )

    assert result["summary"]["decision_count"] == 20
    assert result["baseline"]["decision_count"] == 20
    assert len(result["groups"]) == 2

    payer_a = next(
        item
        for item in result["groups"]
        if item["dimensions"]["insurance"] == "Payer A"
    )

    payer_b = next(
        item
        for item in result["groups"]
        if item["dimensions"]["insurance"] == "Payer B"
    )

    assert payer_a["decision_count"] == 10
    assert payer_a["observed_denial_rate"] == 0.5
    assert payer_a["sample_state"] == "preliminary"

    assert payer_b["decision_count"] == 10
    assert payer_b["observed_denial_rate"] == 0.2
    assert payer_b["sample_state"] == "preliminary"

    payer_a_evaluation = next(
        item
        for item in result["evaluations"]
        if item["dimensions"]["insurance"] == "Payer A"
    )

    assert payer_a_evaluation["triggered"] is True


def test_build_denial_insights_excludes_follow_up_outcomes_from_summary():
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Payer A",
            "insurance_plan": "Gold",
            "requested_days": 5,
            "approved_days": 0,
            "denied_days": 5,
            "decision_at": "2026-09-01T12:00:00+00:00",
        }
    )

    assert auth is not None

    updated = update_auth(
        auth["id"],
        {
            "p2p_requested": True,
            "p2p_decided_at": "2026-09-03T12:00:00+00:00",
            "p2p_outcome": "Overturned",
        },
    )

    assert updated is not None

    result = build_denial_insights(
        dimensions=["insurance"],
    )

    assert result["summary"]["decision_count"] == 1
    assert result["summary"]["denied_count"] == 1
    assert result["summary"]["observed_denial_rate"] == 1.0

    assert len(result["groups"]) == 1
    assert result["groups"][0]["decision_count"] == 1


def test_build_denial_insights_reports_p2p_follow_up_metrics():
    pending_auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Pending P2P",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Payer A",
            "requested_days": 5,
            "denied_days": 5,
            "decision_at": "2026-09-01T12:00:00+00:00",
        }
    )

    assert pending_auth is not None

    pending_update = update_auth(
        pending_auth["id"],
        {
            "p2p_requested": True,
            "p2p_deadline": "2026-09-05",
            "p2p_outcome": "Pending",
        },
    )

    assert pending_update is not None

    overturned_auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Overturned P2P",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Payer A",
            "requested_days": 5,
            "denied_days": 5,
            "decision_at": "2026-09-02T12:00:00+00:00",
        }
    )

    assert overturned_auth is not None

    overturned_update = update_auth(
        overturned_auth["id"],
        {
            "p2p_requested": True,
            "p2p_decided_at": "2026-09-06T12:00:00+00:00",
            "p2p_outcome": "Overturned",
        },
    )

    assert overturned_update is not None

    upheld_auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Upheld P2P",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Denied",
            "insurance": "Payer A",
            "requested_days": 5,
            "denied_days": 5,
            "decision_at": "2026-09-03T12:00:00+00:00",
        }
    )

    assert upheld_auth is not None

    upheld_update = update_auth(
        upheld_auth["id"],
        {
            "p2p_requested": True,
            "p2p_decided_at": "2026-09-07T12:00:00+00:00",
            "p2p_outcome": "Upheld",
        },
    )

    assert upheld_update is not None

    result = build_denial_insights(
        dimensions=["insurance"],
    )

    p2p = result["follow_up_metrics"]["p2p"]

    assert p2p["eligible_count"] == 3
    assert p2p["initiated_count"] == 3
    assert p2p["pending_count"] == 1
    assert p2p["resolved_count"] == 2
    assert p2p["upheld_count"] == 1
    assert p2p["overturned_count"] == 1
    assert p2p["overturn_rate"] == 0.5

    assert result["summary"]["decision_count"] == 3
    assert result["summary"]["denied_count"] == 3


def test_build_denial_insights_supports_filtered_baseline():
    for index in range(5):
        _create_snapshot(
            insurance="Payer A",
            insurance_plan="Gold",
            loc="RTC",
            outcome="Denied",
            decision_at=(f"2026-09-{index + 1:02d}" "T12:00:00+00:00"),
        )

    for index in range(5):
        _create_snapshot(
            insurance="Payer B",
            insurance_plan="Silver",
            loc="PHP",
            outcome="Approved",
            decision_at=(f"2026-09-{index + 10:02d}" "T12:00:00+00:00"),
        )

    result = build_denial_insights(
        dimensions=["insurance"],
        filters={
            "loc": "RTC",
        },
        baseline_filters={
            "loc": "PHP",
        },
    )

    assert result["summary"]["decision_count"] == 5
    assert result["summary"]["observed_denial_rate"] == 1.0

    assert result["baseline"]["decision_count"] == 5
    assert result["baseline"]["observed_denial_rate"] == 0.0
