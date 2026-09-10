from __future__ import annotations

import pytest

from authstatus_api.authorizations.clinical_assessments import (
    InvalidClinicalAssessmentError,
    create_clinical_assessment,
    delete_clinical_assessment,
    get_clinical_assessment,
    list_clinical_assessments,
    update_clinical_assessment,
)
from authstatus_api.authorizations.events import create_auth_event
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
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Pending",
        }
    )

    assert record is not None
    return record


def test_create_clinical_assessment():
    auth = _create_auth()

    assessment = create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 23,
            "assessed_at": "2026-09-01T08:00:00+00:00",
            "loc": "RTC",
        },
    )

    assert assessment is not None
    assert assessment["auth_id"] == auth["id"]
    assert assessment["auth_event_id"] is None
    assert assessment["instrument"] == "CIWA-Ar"
    assert assessment["score"] == 23.0
    assert assessment["assessed_at"] == "2026-09-01T08:00:00+00:00"
    assert assessment["loc"] == "RTC"
    assert assessment["source"] == "manual"


def test_create_clinical_assessment_can_link_auth_event():
    auth = _create_auth()

    event = create_auth_event(
        auth["id"],
        {
            "event_type": "Concurrent Review",
            "event_date": "2026-09-02",
        },
    )

    assert event is not None

    assessment = create_clinical_assessment(
        auth["id"],
        {
            "instrument": "COWS",
            "score": 12,
            "assessed_at": "2026-09-02T09:00:00+00:00",
            "auth_event_id": event["id"],
        },
    )

    assert assessment is not None
    assert assessment["auth_event_id"] == event["id"]


def test_create_clinical_assessment_rejects_event_from_another_auth():
    first_auth = _create_auth()
    second_auth = _create_auth()

    event = create_auth_event(
        second_auth["id"],
        {
            "event_type": "Concurrent Review",
            "event_date": "2026-09-02",
        },
    )

    assert event is not None

    with pytest.raises(
        InvalidClinicalAssessmentError,
        match="auth_event_id must reference an event for this authorization",
    ):
        create_clinical_assessment(
            first_auth["id"],
            {
                "instrument": "CIWA-Ar",
                "score": 23,
                "assessed_at": "2026-09-02T09:00:00+00:00",
                "auth_event_id": event["id"],
            },
        )


def test_list_clinical_assessments_returns_chronological_history():
    auth = _create_auth()

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "PHQ-9",
            "score": 19,
            "assessed_at": "2026-09-04T10:00:00+00:00",
        },
    )

    create_clinical_assessment(
        auth["id"],
        {
            "instrument": "GAD-7",
            "score": 15,
            "assessed_at": "2026-09-03T10:00:00+00:00",
        },
    )

    assessments = list_clinical_assessments(auth["id"])

    assert assessments is not None
    assert [item["instrument"] for item in assessments] == [
        "GAD-7",
        "PHQ-9",
    ]


def test_update_clinical_assessment():
    auth = _create_auth()

    created = create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-Ar",
            "score": 23,
            "assessed_at": "2026-09-01T08:00:00+00:00",
        },
    )

    assert created is not None

    updated = update_clinical_assessment(
        auth["id"],
        created["id"],
        {
            "score": 18,
            "source": "timeline",
        },
    )

    assert updated is not None
    assert updated["score"] == 18.0
    assert updated["source"] == "timeline"
    assert updated["instrument"] == "CIWA-Ar"


def test_delete_clinical_assessment():
    auth = _create_auth()

    created = create_clinical_assessment(
        auth["id"],
        {
            "instrument": "CIWA-B",
            "score": 31,
            "assessed_at": "2026-09-01T08:00:00+00:00",
        },
    )

    assert created is not None

    assert delete_clinical_assessment(
        auth["id"],
        created["id"],
    )

    assert (
        get_clinical_assessment(
            auth["id"],
            created["id"],
        )
        is None
    )


def test_rejects_invalid_assessed_at():
    auth = _create_auth()

    with pytest.raises(
        InvalidClinicalAssessmentError,
        match="assessed_at must be a valid ISO 8601 timestamp",
    ):
        create_clinical_assessment(
            auth["id"],
            {
                "instrument": "CIWA-Ar",
                "score": 23,
                "assessed_at": "not-a-timestamp",
            },
        )
