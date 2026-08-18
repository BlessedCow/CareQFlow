from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.mfa import enable_user_mfa, store_user_mfa_secret
from authstatus_api.security.trusted_devices import (
    get_active_trusted_device_by_token,
)
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_trusted_device_route_settings(tmp_path, monkeypatch):
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
    with TestClient(
        create_app(),
        client=("127.0.0.1", 50000),
    ) as test_client:
        yield test_client


def create_mfa_user():
    user = create_user(
        "trusted-device@example.com",
        "correct horse battery staple",
        role="UR",
    )
    secret = pyotp.random_base32()

    assert store_user_mfa_secret(user["id"], secret) is True
    assert enable_user_mfa(user["id"]) is True

    return user, secret


def start_mfa_login(client: TestClient, username: str):
    response = client.post(
        "/api/security/login",
        json={
            "username": username,
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200
    assert response.json()["mfa_required"] is True

    return response.json()["mfa_challenge_token"]


def trust_device_for_user(
    client: TestClient,
    user: dict,
    secret: str,
) -> str:
    challenge_token = start_mfa_login(client, user["username"])

    response = client.post(
        "/api/security/login/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": pyotp.TOTP(secret).now(),
            "remember_device": True,
        },
    )

    assert response.status_code == 200

    token = client.cookies.get("carequeue_trusted_device")

    assert token

    return token


def test_change_password_revokes_trusted_devices(client):
    user, secret = create_mfa_user()
    trusted_device_token = trust_device_for_user(client, user, secret)

    response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "correct horse battery staple",
            "new_password": "new secure password value",
        },
        headers={
            "X-CSRF-Token": client.cookies.get("carequeue_csrf"),
        },
    )

    assert response.status_code == 200
    assert get_active_trusted_device_by_token(trusted_device_token) is None


def test_admin_password_reset_revokes_target_trusted_devices(client):
    admin = create_user(
        "admin@example.com",
        "admin password value",
        role="Admin",
    )
    user, secret = create_mfa_user()

    trusted_device_token = trust_device_for_user(client, user, secret)

    client.cookies.clear()

    admin_login = client.post(
        "/api/security/login",
        json={
            "username": admin["username"],
            "password": "admin password value",
        },
    )

    assert admin_login.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.post(
        f"/api/security/users/{user['id']}/reset-password",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200
    assert get_active_trusted_device_by_token(trusted_device_token) is None


def test_admin_mfa_reset_revokes_target_trusted_devices(client):
    admin = create_user(
        "admin@example.com",
        "admin password value",
        role="Admin",
    )
    user, secret = create_mfa_user()

    trusted_device_token = trust_device_for_user(client, user, secret)

    client.cookies.clear()

    admin_login = client.post(
        "/api/security/login",
        json={
            "username": admin["username"],
            "password": "admin password value",
        },
    )

    assert admin_login.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.post(
        f"/api/security/users/{user['id']}/reset-mfa",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200
    assert get_active_trusted_device_by_token(trusted_device_token) is None


def test_mfa_verify_creates_trusted_device_when_requested(client):
    user, secret = create_mfa_user()
    challenge_token = start_mfa_login(client, user["username"])

    response = client.post(
        "/api/security/login/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": pyotp.TOTP(secret).now(),
            "remember_device": True,
        },
    )

    assert response.status_code == 200

    token = client.cookies.get("carequeue_trusted_device")

    assert token

    trusted_device = get_active_trusted_device_by_token(token)

    assert trusted_device is not None
    assert trusted_device["user_id"] == user["id"]

    with get_conn() as conn:
        stored_token_hash = conn.execute(
            """
            SELECT token_hash
            FROM trusted_devices
            WHERE id = ?
            """,
            (trusted_device["id"],),
        ).fetchone()[0]

    assert stored_token_hash != token


def test_mfa_verify_does_not_create_trusted_device_by_default(client):
    user, secret = create_mfa_user()
    challenge_token = start_mfa_login(client, user["username"])

    response = client.post(
        "/api/security/login/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": pyotp.TOTP(secret).now(),
        },
    )

    assert response.status_code == 200
    assert client.cookies.get("carequeue_trusted_device") is None

    with get_conn() as conn:
        trusted_device_count = conn.execute(
            "SELECT COUNT(*) FROM trusted_devices"
        ).fetchone()[0]

    assert trusted_device_count == 0


def test_valid_trusted_device_bypasses_mfa_after_password(client):
    user, secret = create_mfa_user()
    challenge_token = start_mfa_login(client, user["username"])

    verify_response = client.post(
        "/api/security/login/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": pyotp.TOTP(secret).now(),
            "remember_device": True,
        },
    )

    assert verify_response.status_code == 200
    trusted_device_token = client.cookies.get("carequeue_trusted_device")

    assert trusted_device_token

    login_response = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["id"] == user["id"]
    assert "mfa_required" not in login_response.json()
    assert "mfa_challenge_token" not in login_response.json()


def test_expired_trusted_device_requires_mfa_again(client):
    user, secret = create_mfa_user()
    challenge_token = start_mfa_login(client, user["username"])

    verify_response = client.post(
        "/api/security/login/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": pyotp.TOTP(secret).now(),
            "remember_device": True,
        },
    )

    assert verify_response.status_code == 200

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE trusted_devices
            SET expires_at = ?
            WHERE user_id = ?
            """,
            (
                "2020-01-01T00:00:00+00:00",
                user["id"],
            ),
        )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["mfa_required"] is True
    assert login_response.json()["mfa_challenge_token"]


def test_trusted_device_cannot_bypass_mfa_for_another_user(client):
    first_user, first_secret = create_mfa_user()
    challenge_token = start_mfa_login(client, first_user["username"])

    verify_response = client.post(
        "/api/security/login/mfa/verify",
        json={
            "challenge_token": challenge_token,
            "code": pyotp.TOTP(first_secret).now(),
            "remember_device": True,
        },
    )

    assert verify_response.status_code == 200

    second_user = create_user(
        "second-trusted-device@example.com",
        "correct horse battery staple",
        role="UR",
    )
    second_secret = pyotp.random_base32()

    assert store_user_mfa_secret(second_user["id"], second_secret) is True
    assert enable_user_mfa(second_user["id"]) is True

    login_response = client.post(
        "/api/security/login",
        json={
            "username": second_user["username"],
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["mfa_required"] is True
    assert login_response.json()["mfa_challenge_token"]


def test_admin_role_change_revokes_target_trusted_devices(client):
    admin = create_user(
        "admin@example.com",
        "admin password value",
        role="Admin",
    )
    user, secret = create_mfa_user()

    trusted_device_token = trust_device_for_user(client, user, secret)

    client.cookies.clear()

    admin_login = client.post(
        "/api/security/login",
        json={
            "username": admin["username"],
            "password": "admin password value",
        },
    )

    assert admin_login.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.patch(
        f"/api/security/users/{user['id']}",
        json={"role": "Read Only"},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200
    assert get_active_trusted_device_by_token(trusted_device_token) is None


def test_admin_account_disable_revokes_target_trusted_devices(client):
    admin = create_user(
        "admin@example.com",
        "admin password value",
        role="Admin",
    )
    user, secret = create_mfa_user()

    trusted_device_token = trust_device_for_user(client, user, secret)

    client.cookies.clear()

    admin_login = client.post(
        "/api/security/login",
        json={
            "username": admin["username"],
            "password": "admin password value",
        },
    )

    assert admin_login.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.patch(
        f"/api/security/users/{user['id']}",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200
    assert get_active_trusted_device_by_token(trusted_device_token) is None


def test_user_can_revoke_all_trusted_devices(client):
    user, secret = create_mfa_user()
    trusted_device_token = trust_device_for_user(client, user, secret)

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.delete(
        "/api/security/mfa/trusted-devices",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200
    assert response.json() == {
        "trusted_devices_revoked": 1,
    }
    assert get_active_trusted_device_by_token(trusted_device_token) is None
    assert client.cookies.get("carequeue_trusted_device") is None


def test_revoke_trusted_devices_returns_zero_when_none_exist(client):
    user = create_user(
        "no-trusted-devices@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.delete(
        "/api/security/mfa/trusted-devices",
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200
    assert response.json() == {
        "trusted_devices_revoked": 0,
    }
