from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from authstatus_api.authorizations.decision_snapshots import (
    create_auth_decision_snapshot,
)
from authstatus_api.authorizations.records import create_auth
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.security.users import create_user
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


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def _login(
    client: TestClient,
    *,
    role: str,
) -> dict[str, str]:
    username = f"{role.lower().replace(' ', '')}@example.com"
    password = "correct horse battery staple"

    create_user(
        username,
        password,
        role=role,
    )

    response = client.post(
        "/api/security/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")
    assert csrf_token

    return {
        "X-CSRF-Token": csrf_token,
    }


def _create_snapshot(
    *,
    insurance: str,
    outcome: str,
    decision_at: str,
) -> None:
    auth = create_auth(
        {
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Pending",
            "insurance": insurance,
        }
    )

    assert auth is not None

    snapshot = create_auth_decision_snapshot(
        auth["id"],
        {
            "outcome": outcome,
            "decision_at": decision_at,
        },
    )

    assert snapshot is not None


@pytest.mark.parametrize(
    "role",
    [
        "Admin",
        "UR",
    ],
)
def test_admin_and_ur_can_query_denial_insights(
    client,
    role,
):
    for index in range(5):
        _create_snapshot(
            insurance="Payer A",
            outcome="Denied",
            decision_at=(f"2026-09-{index + 1:02d}" "T12:00:00+00:00"),
        )

    for index in range(5):
        _create_snapshot(
            insurance="Payer B",
            outcome="Approved",
            decision_at=(f"2026-09-{index + 10:02d}" "T12:00:00+00:00"),
        )

    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
        },
        headers=_login(
            client,
            role=role,
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["summary"]["decision_count"] == 10
    assert data["baseline"]["decision_count"] == 10
    assert len(data["groups"]) == 2
    assert len(data["evaluations"]) == 2


def test_read_only_cannot_query_denial_insights(client):
    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
        },
        headers=_login(
            client,
            role="Read Only",
        ),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Operation not permitted for this role.",
    }


def test_denial_insights_query_requires_authentication(
    client,
):
    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required.",
    }


def test_denial_insights_query_rejects_unsupported_dimension(
    client,
):
    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "client_name",
            ],
        },
        headers=_login(
            client,
            role="UR",
        ),
    )

    assert response.status_code == 400
    assert "Unsupported analytics dimensions" in response.json()["detail"]


def test_denial_insights_query_rejects_unsupported_filter(
    client,
):
    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
            "filters": {
                "client_name": "Test Client",
            },
        },
        headers=_login(
            client,
            role="UR",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Unsupported analytics filter: client_name",
    }


def test_denial_insights_query_rejects_invalid_date_range(
    client,
):
    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
            "start_at": "2026-09-20T00:00:00+00:00",
            "end_at": "2026-09-01T00:00:00+00:00",
        },
        headers=_login(
            client,
            role="Admin",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "end_at cannot be earlier than start_at.",
    }


def test_denial_insights_query_rejects_inverted_sample_thresholds(
    client,
):
    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
            "preliminary_minimum": 20,
            "standard_minimum": 5,
        },
        headers=_login(
            client,
            role="UR",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": ("standard_minimum cannot be lower than " "preliminary_minimum."),
    }


def test_denial_insights_query_applies_custom_rule_thresholds(
    client,
):
    for index in range(10):
        _create_snapshot(
            insurance="Payer A",
            outcome=("Denied" if index < 5 else "Approved"),
            decision_at=(f"2026-09-{index + 1:02d}" "T12:00:00+00:00"),
        )

    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
            "rule_thresholds": {
                "minimum_sample_size": 5,
                "minimum_denial_rate": 0.4,
                "minimum_relative_increase": 0.0,
            },
        },
        headers=_login(
            client,
            role="Admin",
        ),
    )

    assert response.status_code == 200

    evaluation = response.json()["evaluations"][0]

    assert evaluation["minimum_sample_size"] == 5
    assert evaluation["minimum_denial_rate"] == 0.4
    assert evaluation["minimum_relative_increase"] == 0.0


def test_ur_receives_evidence_summary_without_calculation(
    client,
):
    for index in range(5):
        _create_snapshot(
            insurance="Payer A",
            outcome="Denied",
            decision_at=(f"2026-09-{index + 1:02d}" "T12:00:00+00:00"),
        )

    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
        },
        headers=_login(
            client,
            role="UR",
        ),
    )

    assert response.status_code == 200

    evidence = response.json()["evaluations"][0]["evidence_strength"]

    assert "score" in evidence
    assert "level" in evidence
    assert "wilson_95_interval" in evidence
    assert "calculation" not in evidence


def test_admin_can_request_evidence_calculation(
    client,
):
    for index in range(5):
        _create_snapshot(
            insurance="Payer A",
            outcome="Denied",
            decision_at=(f"2026-09-{index + 1:02d}" "T12:00:00+00:00"),
        )

    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
            "include_evidence_calculation": True,
        },
        headers=_login(
            client,
            role="Admin",
        ),
    )

    assert response.status_code == 200

    evidence = response.json()["evaluations"][0]["evidence_strength"]

    assert "calculation" in evidence
    assert evidence["calculation"]["version"] == "1.0"


def test_ur_cannot_request_evidence_calculation(
    client,
):
    response = client.post(
        "/api/denial-insights/query",
        json={
            "dimensions": [
                "insurance",
            ],
            "include_evidence_calculation": True,
        },
        headers=_login(
            client,
            role="UR",
        ),
    )

    assert response.status_code == 403

    assert response.json() == {
        "detail": ("Evidence calculation details are restricted " "to Admin users."),
    }
