from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_backup_route_settings(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_DIRECTORY",
        str(tmp_path / "backups"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def login_headers(
    client: TestClient,
    *,
    username: str,
    password: str,
) -> dict[str, str]:
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


def test_admin_can_list_restore_points(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    response = client.get("/api/admin/system/backups")

    assert response.status_code == 200
    assert response.json() == {"backups": []}


def test_admin_can_create_verified_restore_point(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    headers = login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    response = client.post(
        "/api/admin/system/backups",
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["verified"] is True
    assert data["backup"]["filename"].endswith(".db.enc")
    assert data["backup"]["size_bytes"] > 0
    assert data["backup"]["created_at"]

    list_response = client.get("/api/admin/system/backups")

    assert list_response.status_code == 200
    assert list_response.json()["backups"] == [
        data["backup"],
    ]


def test_admin_can_verify_existing_restore_point(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    headers = login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    create_response = client.post(
        "/api/admin/system/backups",
        headers=headers,
    )
    filename = create_response.json()["backup"]["filename"]

    response = client.post(
        "/api/admin/system/backups/verify",
        json={"filename": filename},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": filename,
        "verified": True,
    }


def test_backup_actions_are_recorded_in_audit_log(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    headers = login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    create_response = client.post(
        "/api/admin/system/backups",
        headers=headers,
    )
    filename = create_response.json()["backup"]["filename"]

    verify_response = client.post(
        "/api/admin/system/backups/verify",
        json={"filename": filename},
        headers=headers,
    )

    assert verify_response.status_code == 200

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT action, resource_type, metadata
            FROM audit_events
            WHERE action IN ('backup.create', 'backup.verify')
            ORDER BY id
            """).fetchall()

    assert [row["action"] for row in rows] == [
        "backup.create",
        "backup.verify",
    ]
    assert all(row["resource_type"] == "backup" for row in rows)

    metadata = [json.loads(row["metadata"]) for row in rows]

    assert metadata == [
        {
            "filename": filename,
            "verified": True,
        },
        {
            "filename": filename,
            "verified": True,
        },
    ]


def test_non_admin_cannot_list_restore_points(client):
    create_user(
        "ur@example.com",
        "correct horse battery staple",
        role="UR",
    )
    login_headers(
        client,
        username="ur@example.com",
        password="correct horse battery staple",
    )

    response = client.get("/api/admin/system/backups")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Operation not permitted for this role.",
    }


def test_non_admin_cannot_create_restore_point(client):
    create_user(
        "ur@example.com",
        "correct horse battery staple",
        role="UR",
    )
    headers = login_headers(
        client,
        username="ur@example.com",
        password="correct horse battery staple",
    )

    response = client.post(
        "/api/admin/system/backups",
        headers=headers,
    )

    assert response.status_code == 403


def test_verification_rejects_unsafe_filename(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    headers = login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    response = client.post(
        "/api/admin/system/backups/verify",
        json={
            "filename": "../outside.db.enc",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "The selected restore point could not be verified.",
    }
    assert "outside" not in response.text


def test_create_restore_point_requires_csrf_token(client):
    create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    login_headers(
        client,
        username="admin@example.com",
        password="correct horse battery staple",
    )

    response = client.post("/api/admin/system/backups")

    assert response.status_code == 403
