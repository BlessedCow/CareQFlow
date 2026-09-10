from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.security.users import create_user
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


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client):
    create_user(
        "ur@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/login",
        json={
            "username": "ur@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")
    assert csrf_token

    return {"X-CSRF-Token": csrf_token}


def _create_auth(client, auth_headers) -> int:
    response = client.post(
        "/api/auths",
        json={
            "facility": "Facility A",
            "client_name": "Test Client",
            "loc": "RTC",
            "submission_methods": "Fax",
            "auth_type": "Concurrent",
            "status": "Pending",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    return int(response.json()["id"])


def test_create_decision_snapshot_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth_id}/decision-snapshots",
        json={
            "facility": "Facility A",
            "loc": "RTC",
            "auth_type": "Concurrent",
            "outcome": "Approved",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["outcome"] == "Approved"


def test_list_decision_snapshots_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    created = client.post(
        f"/api/auths/{auth_id}/decision-snapshots",
        json={
            "facility": "Facility A",
            "loc": "RTC",
            "auth_type": "Concurrent",
            "outcome": "Denied",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert created.status_code == 201

    response = client.get(
        f"/api/auths/{auth_id}/decision-snapshots",
    )

    assert response.status_code == 200
    assert len(response.json()["snapshots"]) == 1


def test_create_snapshot_returns_404_for_missing_auth(
    client,
    auth_headers,
):
    response = client.post(
        "/api/auths/999/decision-snapshots",
        json={
            "facility": "Facility A",
            "loc": "RTC",
            "auth_type": "Concurrent",
            "outcome": "Denied",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_create_snapshot_rejects_invalid_timestamp(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth_id}/decision-snapshots",
        json={
            "facility": "Facility A",
            "loc": "RTC",
            "auth_type": "Concurrent",
            "outcome": "Denied",
            "decision_at": "not-a-timestamp",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400


def test_read_only_user_can_view_snapshots(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    created = client.post(
        f"/api/auths/{auth_id}/decision-snapshots",
        json={
            "facility": "Facility A",
            "loc": "RTC",
            "auth_type": "Concurrent",
            "outcome": "Approved",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert created.status_code == 201

    client.post(
        "/api/security/logout",
        headers=auth_headers,
    )

    create_user(
        "readonly@example.com",
        "correct horse battery staple",
        role="Read Only",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "readonly@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    response = client.get(
        f"/api/auths/{auth_id}/decision-snapshots",
    )

    assert response.status_code == 200


def test_read_only_user_cannot_create_snapshot(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    client.post(
        "/api/security/logout",
        headers=auth_headers,
    )

    create_user(
        "readonly@example.com",
        "correct horse battery staple",
        role="Read Only",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "readonly@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")
    assert csrf_token

    response = client.post(
        f"/api/auths/{auth_id}/decision-snapshots",
        json={
            "facility": "Facility A",
            "loc": "RTC",
            "auth_type": "Concurrent",
            "outcome": "Denied",
            "decision_at": "2026-09-10T12:00:00+00:00",
        },
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 403
