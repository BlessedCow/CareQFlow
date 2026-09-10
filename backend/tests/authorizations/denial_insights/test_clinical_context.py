from __future__ import annotations

import pytest

from authstatus_api.authorizations.clinical_assessments import (
    create_clinical_assessment,
)
from authstatus_api.authorizations.decision_snapshots import (
    create_auth_decision_snapshot,
)
from authstatus_api.authorizations.denial_insights.clinical_context import (
    enrich_snapshots_with_clinical_context,
)
from authstatus_api.authorizations.events import create_auth_event
from authstatus_api.authorizations.records import create_auth
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def _create_auth() -> dict:
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Pending",
        }
    )

    assert auth is not None
    return auth


def _create_snapshot(
    auth_id: int,
    *,
    decision_at: str,
    auth_event_id: int | None = None,
) -> dict:
    snapshot = create_auth_decision_snapshot(
        auth_id,
        {
            "outcome": "Denied",
            "decision_at": decision_at,
            "auth_event_id": auth_event_id,
        },
    )

    assert snapshot is not None
    return snapshot


def test_uses_latest_assessment_before_decision():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 18,
            "assessed_at": "2026-09-08T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 23,
            "assessed_at": "2026-09-09T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])

    assert result[0]["clinical_instrument"] == "CIWA-Ar"
    assert result[0]["clinical_latest_score"] == 23.0
    assert result[0]["clinical_score_age_days"] == 1


def test_future_assessment_does_not_affect_earlier_decision():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "PHQ-9",
            "score": 12,
            "assessed_at": "2026-09-09T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "PHQ-9",
            "score": 24,
            "assessed_at": "2026-09-11T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])

    assert result[0]["clinical_latest_score"] == 12.0
    assert result[0]["clinical_score_age_days"] == 1


def test_future_only_assessment_returns_unknown_context():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "GAD-7",
            "score": 18,
            "assessed_at": "2026-09-12T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])

    assert result[0]["clinical_instrument"] is None
    assert result[0]["clinical_latest_score"] is None
    assert result[0]["clinical_score_age_days"] is None


def test_prefers_assessment_linked_to_same_auth_event():
    auth = _create_auth()

    event = create_auth_event(
        auth["id"],
        {
            "event_type": "Concurrent Review",
            "event_date": "2026-09-10",
        },
    )

    assert event is not None

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 24,
            "assessed_at": "2026-09-09T08:00:00+00:00",
            "auth_event_id": event["id"],
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 30,
            "assessed_at": "2026-09-10T07:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
        auth_event_id=event["id"],
    )

    result = enrich_snapshots_with_clinical_context([snapshot])

    assert result[0]["clinical_latest_score"] == 24.0


def test_uses_latest_available_assessment_when_event_has_none():
    auth = _create_auth()

    event = create_auth_event(
        auth["id"],
        {
            "event_type": "Concurrent Review",
            "event_date": "2026-09-10",
        },
    )

    assert event is not None

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "COWS",
            "score": 14,
            "assessed_at": "2026-09-10T06:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
        auth_event_id=event["id"],
    )

    result = enrich_snapshots_with_clinical_context([snapshot])

    assert result[0]["clinical_instrument"] == "COWS"
    assert result[0]["clinical_latest_score"] == 14.0


def test_score_age_uses_elapsed_complete_days():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "PHQ-9",
            "score": 17,
            "assessed_at": "2026-09-08T20:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])

    assert result[0]["clinical_score_age_days"] == 1


def test_clinical_history_calculates_change_and_increasing_trend():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 18,
            "assessed_at": "2026-09-08T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 23,
            "assessed_at": "2026-09-09T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])[0]

    assert result["clinical_score_change"] == 5.0
    assert result["clinical_score_trend"] == "increasing"
    assert result["clinical_assessment_count"] == 2
    assert result["clinical_min_score"] == 18.0
    assert result["clinical_max_score"] == 23.0


def test_clinical_history_calculates_decreasing_trend():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "COWS",
            "score": 16,
            "assessed_at": "2026-09-08T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "COWS",
            "score": 10,
            "assessed_at": "2026-09-09T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])[0]

    assert result["clinical_score_change"] == -6.0
    assert result["clinical_score_trend"] == "decreasing"


def test_clinical_history_calculates_stable_trend():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "PHQ-9",
            "score": 17,
            "assessed_at": "2026-09-08T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "PHQ-9",
            "score": 17,
            "assessed_at": "2026-09-09T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])[0]

    assert result["clinical_score_change"] == 0.0
    assert result["clinical_score_trend"] == "stable"


def test_clinical_history_with_single_assessment_has_unknown_trend():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "GAD-7",
            "score": 14,
            "assessed_at": "2026-09-09T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])[0]

    assert result["clinical_score_change"] is None
    assert result["clinical_score_trend"] is None
    assert result["clinical_assessment_count"] == 1
    assert result["clinical_min_score"] == 14.0
    assert result["clinical_max_score"] == 14.0


def test_clinical_history_does_not_mix_instruments():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "PHQ-9",
            "score": 20,
            "assessed_at": "2026-09-07T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 18,
            "assessed_at": "2026-09-08T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 24,
            "assessed_at": "2026-09-09T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])[0]

    assert result["clinical_instrument"] == "CIWA-Ar"
    assert result["clinical_assessment_count"] == 2
    assert result["clinical_score_change"] == 6.0
    assert result["clinical_min_score"] == 18.0
    assert result["clinical_max_score"] == 24.0


def test_clinical_history_ignores_future_scores():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-B",
            "score": 25,
            "assessed_at": "2026-09-08T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-B",
            "score": 30,
            "assessed_at": "2026-09-09T08:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-B",
            "score": 40,
            "assessed_at": "2026-09-11T08:00:00+00:00",
        },
    )

    snapshot = _create_snapshot(
        auth["id"],
        decision_at="2026-09-10T08:00:00+00:00",
    )

    result = enrich_snapshots_with_clinical_context([snapshot])[0]

    assert result["clinical_latest_score"] == 30.0
    assert result["clinical_score_change"] == 5.0
    assert result["clinical_assessment_count"] == 2
    assert result["clinical_max_score"] == 30.0
