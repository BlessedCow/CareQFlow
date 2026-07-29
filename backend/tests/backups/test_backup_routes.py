from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from authstatus_api.backups import router as backup_router
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
    monkeypatch.setenv(
        "AUTHSTATUS_RESTORE_DIRECTORY",
        str(tmp_path / "restores"),
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
    assert data["retention"] == {
        "retention_days": 90,
        "minimum_count": 5,
        "deleted": [],
        "protected": [],
        "failed": [],
    }

    list_response = client.get("/api/admin/system/backups")

    assert list_response.status_code == 200
    assert list_response.json()["backups"] == [
        data["backup"],
    ]


def test_admin_restore_point_reports_retention_cleanup(
    client,
    monkeypatch,
):
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

    monkeypatch.setattr(
        backup_router,
        "prune_encrypted_database_backups",
        lambda **_kwargs: {
            "deleted": [
                "auth_tracker_20260101_120000_000001.db.enc",
            ],
            "protected": [
                "auth_tracker_20260102_120000_000001.db.enc",
            ],
            "retained": [],
            "failed": [],
        },
    )

    response = client.post(
        "/api/admin/system/backups",
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["verified"] is True
    assert data["retention"] == {
        "retention_days": 90,
        "minimum_count": 5,
        "deleted": [
            "auth_tracker_20260101_120000_000001.db.enc",
        ],
        "protected": [
            "auth_tracker_20260102_120000_000001.db.enc",
        ],
        "failed": [],
    }


def test_admin_restore_point_survives_retention_exception(
    client,
    monkeypatch,
):
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

    def raise_retention_error(**_kwargs):
        raise backup_router.BackupRetentionError("retention unavailable")

    monkeypatch.setattr(
        backup_router,
        "prune_encrypted_database_backups",
        raise_retention_error,
    )

    response = client.post(
        "/api/admin/system/backups",
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["verified"] is True
    assert data["backup"]["filename"].endswith(".db.enc")
    assert data["retention"] == {
        "retention_days": 90,
        "minimum_count": 5,
        "deleted": [],
        "protected": [],
        "failed": [
            "Backup retention cleanup could not be completed.",
        ],
    }


def test_admin_restore_point_reports_individual_prune_failures(
    client,
    monkeypatch,
):
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

    monkeypatch.setattr(
        backup_router,
        "prune_encrypted_database_backups",
        lambda **_kwargs: {
            "deleted": [],
            "protected": [],
            "retained": [],
            "failed": [
                {
                    "filename": ("auth_tracker_20260101_120000_000001.db.enc"),
                    "reason": "access denied",
                }
            ],
        },
    )

    response = client.post(
        "/api/admin/system/backups",
        headers=headers,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["verified"] is True
    assert data["retention"]["failed"] == [
        "auth_tracker_20260101_120000_000001.db.enc",
    ]
    assert "access denied" not in response.text


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
            "retention_days": 90,
            "retention_minimum_count": 5,
            "retention_deleted": [],
            "retention_protected": [],
            "retention_failed": [],
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


def test_admin_can_read_empty_recovery_status(client):
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

    response = client.get("/api/admin/system/backups/recovery")

    assert response.status_code == 200
    assert response.json() == {
        "pending": False,
        "recovery": None,
    }


def test_admin_can_stage_and_read_database_recovery(client):
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

    stage_response = client.post(
        "/api/admin/system/backups/recovery/stage",
        json={"filename": filename},
        headers=headers,
    )

    assert stage_response.status_code == 201

    stage_data = stage_response.json()

    assert stage_data["staged"] is True
    assert stage_data["recovery"]["backup_filename"] == filename
    assert stage_data["recovery"]["staged_filename"].endswith(".restored.db")
    assert stage_data["recovery"]["staged_at"]

    status_response = client.get("/api/admin/system/backups/recovery")

    assert status_response.status_code == 200
    assert status_response.json() == {
        "pending": True,
        "recovery": stage_data["recovery"],
    }


def test_admin_can_cancel_staged_database_recovery(client):
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

    stage_response = client.post(
        "/api/admin/system/backups/recovery/stage",
        json={"filename": filename},
        headers=headers,
    )
    recovery = stage_response.json()["recovery"]

    cancel_response = client.delete(
        "/api/admin/system/backups/recovery",
        headers=headers,
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json() == {
        "recovery": recovery,
        "canceled": True,
    }

    status_response = client.get("/api/admin/system/backups/recovery")

    assert status_response.json() == {
        "pending": False,
        "recovery": None,
    }


def test_staging_second_recovery_is_rejected(client):
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

    first_response = client.post(
        "/api/admin/system/backups/recovery/stage",
        json={"filename": filename},
        headers=headers,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/admin/system/backups/recovery/stage",
        json={"filename": filename},
        headers=headers,
    )

    assert second_response.status_code == 400
    assert second_response.json() == {
        "detail": "The selected restore point could not be staged.",
    }


def test_recovery_actions_are_recorded_in_audit_log(client):
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

    stage_response = client.post(
        "/api/admin/system/backups/recovery/stage",
        json={"filename": filename},
        headers=headers,
    )

    assert stage_response.status_code == 201

    cancel_response = client.delete(
        "/api/admin/system/backups/recovery",
        headers=headers,
    )

    assert cancel_response.status_code == 200

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT action, resource_type, metadata
            FROM audit_events
            WHERE action IN (
                'recovery.stage',
                'recovery.cancel'
            )
            ORDER BY id
            """).fetchall()

    assert [row["action"] for row in rows] == [
        "recovery.stage",
        "recovery.cancel",
    ]
    assert all(row["resource_type"] == "database_recovery" for row in rows)

    metadata = [json.loads(row["metadata"]) for row in rows]

    assert all(item["backup_filename"] == filename for item in metadata)
    assert all(item["staged_filename"].endswith(".restored.db") for item in metadata)


def test_non_admin_cannot_manage_database_recovery(client):
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

    status_response = client.get("/api/admin/system/backups/recovery")
    stage_response = client.post(
        "/api/admin/system/backups/recovery/stage",
        json={"filename": "backup.db.enc"},
        headers=headers,
    )
    cancel_response = client.delete(
        "/api/admin/system/backups/recovery",
        headers=headers,
    )

    assert status_response.status_code == 403
    assert stage_response.status_code == 403
    assert cancel_response.status_code == 403


def test_recovery_mutations_require_csrf_token(client):
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

    stage_response = client.post(
        "/api/admin/system/backups/recovery/stage",
        json={"filename": "backup.db.enc"},
    )
    cancel_response = client.delete("/api/admin/system/backups/recovery")

    assert stage_response.status_code == 403
    assert cancel_response.status_code == 403
