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

    return {
        "X-CSRF-Token": csrf_token,
    }


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


def _episode_payload() -> dict:
    return {
        "loc": "RTC",
        "started_at": "2026-09-01T08:00:00+00:00",
        "source": "manual",
    }


def test_create_auth_loc_episode_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json=_episode_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["auth_id"] == auth_id
    assert data["loc"] == "RTC"
    assert data["started_at"] == "2026-09-01T08:00:00+00:00"
    assert data["ended_at"] is None
    assert data["source"] == "manual"


def test_list_auth_loc_episodes_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    first_response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json={
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
            "ended_at": "2026-09-05T10:00:00+00:00",
        },
        headers=auth_headers,
    )
    second_response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json={
            "loc": "PHP",
            "started_at": "2026-09-05T10:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get(
        f"/api/auths/{auth_id}/loc-episodes",
    )

    assert response.status_code == 200

    episodes = response.json()["episodes"]

    assert [episode["loc"] for episode in episodes] == [
        "RTC",
        "PHP",
    ]


def test_update_auth_loc_episode_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    create_response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json=_episode_payload(),
        headers=auth_headers,
    )

    assert create_response.status_code == 201

    episode_id = create_response.json()["id"]

    response = client.patch(
        f"/api/auths/{auth_id}/loc-episodes/{episode_id}",
        json={
            "loc": "PHP",
            "source": "timeline",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["loc"] == "PHP"
    assert data["source"] == "timeline"


def test_delete_auth_loc_episode_endpoint(client, auth_headers):
    auth_id = _create_auth(client, auth_headers)

    create_response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json=_episode_payload(),
        headers=auth_headers,
    )

    assert create_response.status_code == 201

    episode_id = create_response.json()["id"]

    response = client.delete(
        f"/api/auths/{auth_id}/loc-episodes/{episode_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "deleted": True,
        "id": episode_id,
    }


def test_create_auth_loc_episode_returns_404_for_missing_auth(
    client,
    auth_headers,
):
    response = client.post(
        "/api/auths/999/loc-episodes",
        json=_episode_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Auth record not found.",
    }


def test_list_auth_loc_episodes_returns_404_for_missing_auth(
    client,
    auth_headers,
):
    response = client.get(
        "/api/auths/999/loc-episodes",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Auth record not found.",
    }


def test_update_auth_loc_episode_returns_404_for_missing_episode(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    response = client.patch(
        f"/api/auths/{auth_id}/loc-episodes/999",
        json={"loc": "PHP"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Authorization LOC episode not found.",
    }


def test_delete_auth_loc_episode_returns_404_for_missing_episode(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    response = client.delete(
        f"/api/auths/{auth_id}/loc-episodes/999",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Authorization LOC episode not found.",
    }


def test_create_auth_loc_episode_rejects_invalid_window(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json={
            "loc": "RTC",
            "started_at": "2026-09-05T10:00:00+00:00",
            "ended_at": "2026-09-01T08:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "ended_at cannot be earlier than started_at.",
    }


def test_create_auth_loc_episode_rejects_overlap(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    first_response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json={
            "loc": "RTC",
            "started_at": "2026-09-01T08:00:00+00:00",
            "ended_at": "2026-09-05T10:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert first_response.status_code == 201

    response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json={
            "loc": "PHP",
            "started_at": "2026-09-04T08:00:00+00:00",
            "ended_at": "2026-09-06T08:00:00+00:00",
        },
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "The LOC episode overlaps an existing episode.",
    }


def test_read_only_user_can_view_auth_loc_episodes(
    client,
    auth_headers,
):
    auth_id = _create_auth(client, auth_headers)

    create_response = client.post(
        f"/api/auths/{auth_id}/loc-episodes",
        json=_episode_payload(),
        headers=auth_headers,
    )

    assert create_response.status_code == 201

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
        f"/api/auths/{auth_id}/loc-episodes",
    )

    assert response.status_code == 200
    assert len(response.json()["episodes"]) == 1


def test_read_only_user_cannot_create_auth_loc_episode(
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
        f"/api/auths/{auth_id}/loc-episodes",
        json=_episode_payload(),
        headers={
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Operation not permitted for this role.",
    }
