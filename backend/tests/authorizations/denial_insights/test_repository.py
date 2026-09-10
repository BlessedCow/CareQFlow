from __future__ import annotations

import pytest

from authstatus_api.authorizations.decision_snapshots import (
    create_auth_decision_snapshot,
)
from authstatus_api.authorizations.denial_insights.repository import (
    InvalidDenialInsightsFilterError,
    build_denial_insights,
    list_decision_snapshots,
)
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
