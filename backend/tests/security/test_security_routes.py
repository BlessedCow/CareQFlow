from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.mfa import enable_user_mfa, store_user_mfa_secret
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", generate_encryption_key())
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(tmp_path / "auth_tracker.db"))
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


def auth_headers_for(
    client: TestClient,
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
    assert client.cookies.get("carequeue_session")

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    return {
        "X-CSRF-Token": csrf_token,
    }


def csrf_headers(client: TestClient) -> dict[str, str]:
    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    return {
        "X-CSRF-Token": csrf_token,
    }


def test_login_returns_user_without_session_token(client):
    create_user("user@example.com", "correct horse battery staple", role="Admin")

    response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "user": {
            "id": data["user"]["id"],
            "username": "user@example.com",
            "role": "Admin",
            "is_active": True,
            "last_login_at": data["user"]["last_login_at"],
            "password_changed_at": data["user"]["password_changed_at"],
            "must_change_password": False,
            "mfa_enabled": False,
        },
        "session": {
            "expires_at": data["session"]["expires_at"],
        },
    }
    assert data["session"]["expires_at"]
    assert data["user"]["role"] == "Admin"
    assert "password_hash" not in data["user"]


def test_second_login_revokes_first_active_session(client):
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    first_login = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": "correct horse battery staple",
        },
    )

    assert first_login.status_code == 200

    first_token = client.cookies.get("carequeue_session")

    assert first_token

    with TestClient(
        create_app(),
        client=("127.0.0.1", 50001),
    ) as second_client:
        second_login = second_client.post(
            "/api/security/login",
            json={
                "username": user["username"],
                "password": "correct horse battery staple",
            },
        )

        assert second_login.status_code == 200

        second_token = second_client.cookies.get("carequeue_session")

        assert second_token
        assert second_token != first_token

        first_me = client.get("/api/security/me")
        second_me = second_client.get("/api/security/me")

    assert first_me.status_code == 401
    assert second_me.status_code == 200
    assert second_me.json()["user"]["username"] == user["username"]


def test_second_mfa_login_revokes_first_active_session(client):
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )
    secret = pyotp.random_base32()

    assert store_user_mfa_secret(user["id"], secret) is True
    assert enable_user_mfa(user["id"]) is True

    first_login = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": "correct horse battery staple",
        },
    )

    assert first_login.status_code == 200
    assert first_login.json()["mfa_required"] is True

    first_verify = client.post(
        "/api/security/login/mfa/verify",
        json={
            "challenge_token": first_login.json()["mfa_challenge_token"],
            "code": pyotp.TOTP(secret).now(),
        },
    )

    assert first_verify.status_code == 200

    first_token = client.cookies.get("carequeue_session")

    assert first_token

    with TestClient(
        create_app(),
        client=("127.0.0.1", 50001),
    ) as second_client:
        second_login = second_client.post(
            "/api/security/login",
            json={
                "username": user["username"],
                "password": "correct horse battery staple",
            },
        )

        assert second_login.status_code == 200
        assert second_login.json()["mfa_required"] is True

        second_verify = second_client.post(
            "/api/security/login/mfa/verify",
            json={
                "challenge_token": second_login.json()["mfa_challenge_token"],
                "code": pyotp.TOTP(secret).now(),
            },
        )

        assert second_verify.status_code == 200

        second_token = second_client.cookies.get("carequeue_session")

        assert second_token
        assert second_token != first_token

        first_me = client.get("/api/security/me")
        second_me = second_client.get("/api/security/me")

    assert first_me.status_code == 401
    assert second_me.status_code == 200


def test_login_rejects_wrong_password(client):
    create_user("user@example.com", "correct horse battery staple", role="UR")

    response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "wrong password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password."}


def test_failed_login_does_not_set_csrf_cookie(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "wrong password",
        },
    )

    assert response.status_code == 401
    assert client.cookies.get("carequeue_csrf") is None


def test_failed_login_writes_audit_event(client):
    create_user("user@example.com", "correct horse battery staple", role="UR")

    response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "wrong password",
        },
    )

    assert response.status_code == 401

    with get_conn() as conn:
        row = conn.execute("""
            SELECT action, username, metadata
            FROM audit_events
            """).fetchone()

    assert row["action"] == "security.login_failed"
    assert row["username"] == "user@example.com"


def test_login_temporarily_locks_account_after_repeated_failures(client):
    create_user("user@example.com", "correct horse battery staple", role="UR")

    for _ in range(5):
        response = client.post(
            "/api/security/login",
            json={
                "username": "user@example.com",
                "password": "wrong password",
            },
        )

        assert response.status_code == 401

    response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 423
    assert response.json() == {
        "detail": "Account is temporarily locked. Try again later.",
    }


def test_locked_login_writes_audit_event(client):
    create_user("user@example.com", "correct horse battery staple", role="UR")

    for _ in range(5):
        client.post(
            "/api/security/login",
            json={
                "username": "user@example.com",
                "password": "wrong password",
            },
        )

    response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 423

    with get_conn() as conn:
        row = conn.execute("""
            SELECT action, username, metadata
            FROM audit_events
            WHERE action = 'security.login_locked'
            """).fetchone()

    assert row is not None
    assert row["action"] == "security.login_locked"
    assert row["username"] == "user@example.com"


def test_login_rejects_unknown_user(client):
    response = client.post(
        "/api/security/login",
        json={
            "username": "missing@example.com",
            "password": "password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password."}


def test_me_returns_current_user(client):
    create_user("user@example.com", "correct horse battery staple", role="UR")

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    response = client.get("/api/security/me")

    assert response.status_code == 200

    data = response.json()

    assert data["user"]["username"] == "user@example.com"
    assert data["user"]["role"] == "UR"
    assert data["session"]["expires_at"]


def test_mfa_status_reports_disabled_without_pending_enrollment(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    auth_headers_for(
        client,
        "user@example.com",
        "correct horse battery staple",
    )

    response = client.get("/api/security/mfa/status")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": False,
        "enrollment_pending": False,
    }


def test_user_can_start_mfa_enrollment(client):
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "correct horse battery staple",
        },
        headers=auth_headers_for(
            client,
            "user@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["secret"]
    assert data["provisioning_uri"].startswith("otpauth://totp/")
    assert "CareQueue" in data["provisioning_uri"]

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT mfa_enabled, mfa_secret
            FROM users
            WHERE id = ?
            """,
            (user["id"],),
        ).fetchone()

    assert row is not None
    assert row["mfa_enabled"] == 0
    assert row["mfa_secret"]
    assert row["mfa_secret"] != data["secret"]


def test_mfa_enrollment_requires_correct_current_password(client):
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "wrong password",
        },
        headers=auth_headers_for(
            client,
            "user@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Current password is incorrect.",
    }

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT mfa_enabled, mfa_secret
            FROM users
            WHERE id = ?
            """,
            (user["id"],),
        ).fetchone()

    assert row is not None
    assert row["mfa_enabled"] == 0
    assert row["mfa_secret"] is None


def test_mfa_status_reports_pending_enrollment(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    headers = auth_headers_for(
        client,
        "user@example.com",
        "correct horse battery staple",
    )

    enrollment_response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "correct horse battery staple",
        },
        headers=headers,
    )

    assert enrollment_response.status_code == 200

    response = client.get("/api/security/mfa/status")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": False,
        "enrollment_pending": True,
    }


def test_mfa_enrollment_confirm_rejects_without_pending_enrollment(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/mfa/enroll/confirm",
        json={
            "code": "123456",
        },
        headers=auth_headers_for(
            client,
            "user@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "MFA enrollment has not been started.",
    }


def test_mfa_enrollment_confirm_rejects_invalid_code(client):
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    headers = auth_headers_for(
        client,
        "user@example.com",
        "correct horse battery staple",
    )

    enrollment_response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "correct horse battery staple",
        },
        headers=headers,
    )

    assert enrollment_response.status_code == 200

    response = client.post(
        "/api/security/mfa/enroll/confirm",
        json={
            "code": "000000",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid authentication code.",
    }

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT mfa_enabled
            FROM users
            WHERE id = ?
            """,
            (user["id"],),
        ).fetchone()

    assert row is not None
    assert row["mfa_enabled"] == 0


def test_user_can_confirm_mfa_enrollment(client):
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    headers = auth_headers_for(
        client,
        "user@example.com",
        "correct horse battery staple",
    )

    enrollment_response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "correct horse battery staple",
        },
        headers=headers,
    )

    assert enrollment_response.status_code == 200

    secret = enrollment_response.json()["secret"]
    code = pyotp.TOTP(secret).now()

    response = client.post(
        "/api/security/mfa/enroll/confirm",
        json={
            "code": code,
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
    }

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT mfa_enabled
            FROM users
            WHERE id = ?
            """,
            (user["id"],),
        ).fetchone()

    assert row is not None
    assert row["mfa_enabled"] == 1


def test_mfa_status_reports_enabled_after_confirmation(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    headers = auth_headers_for(
        client,
        "user@example.com",
        "correct horse battery staple",
    )

    enrollment_response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "correct horse battery staple",
        },
        headers=headers,
    )

    secret = enrollment_response.json()["secret"]

    confirm_response = client.post(
        "/api/security/mfa/enroll/confirm",
        json={
            "code": pyotp.TOTP(secret).now(),
        },
        headers=headers,
    )

    assert confirm_response.status_code == 200

    response = client.get("/api/security/mfa/status")

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "enrollment_pending": False,
    }


def test_mfa_enrollment_writes_safe_audit_events(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    headers = auth_headers_for(
        client,
        "user@example.com",
        "correct horse battery staple",
    )

    enrollment_response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "correct horse battery staple",
        },
        headers=headers,
    )

    assert enrollment_response.status_code == 200

    secret = enrollment_response.json()["secret"]
    code = pyotp.TOTP(secret).now()

    confirm_response = client.post(
        "/api/security/mfa/enroll/confirm",
        json={
            "code": code,
        },
        headers=headers,
    )

    assert confirm_response.status_code == 200

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT action, metadata
            FROM audit_events
            WHERE action IN (
                'security.mfa_enrollment_started',
                'security.mfa_enabled'
            )
            ORDER BY id
            """).fetchall()

    assert [row["action"] for row in rows] == [
        "security.mfa_enrollment_started",
        "security.mfa_enabled",
    ]

    for row in rows:
        assert secret not in row["metadata"]
        assert code not in row["metadata"]


def test_failed_mfa_enrollment_attempts_are_audited(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    headers = auth_headers_for(
        client,
        "user@example.com",
        "correct horse battery staple",
    )

    wrong_password_response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "wrong password",
        },
        headers=headers,
    )

    assert wrong_password_response.status_code == 400

    enrollment_response = client.post(
        "/api/security/mfa/enroll",
        json={
            "current_password": "correct horse battery staple",
        },
        headers=headers,
    )

    assert enrollment_response.status_code == 200

    invalid_code_response = client.post(
        "/api/security/mfa/enroll/confirm",
        json={
            "code": "000000",
        },
        headers=headers,
    )

    assert invalid_code_response.status_code == 400

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT action
            FROM audit_events
            WHERE action IN (
                'security.mfa_enrollment_password_failed',
                'security.mfa_enrollment_verification_failed'
            )
            ORDER BY id
            """).fetchall()

    assert [row["action"] for row in rows] == [
        "security.mfa_enrollment_password_failed",
        "security.mfa_enrollment_verification_failed",
    ]


def test_login_sets_httponly_session_cookie(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200

    set_cookie = response.headers["set-cookie"]

    assert "carequeue_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/api" in set_cookie


def test_login_sets_readable_csrf_cookie(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    set_cookie_headers = response.headers.get_list("set-cookie")
    csrf_cookie_header = next(
        header for header in set_cookie_headers if header.startswith("carequeue_csrf=")
    )

    assert "HttpOnly" not in csrf_cookie_header
    assert "SameSite=lax" in csrf_cookie_header
    assert "Path=/" in csrf_cookie_header


def test_session_cookie_authenticates_without_bearer_header(
    client,
):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    response = client.get("/api/security/me")

    assert response.status_code == 200
    assert response.json()["user"]["username"] == ("user@example.com")


def test_bearer_header_does_not_authenticate_without_cookie(
    client,
):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    token = client.cookies.get("carequeue_session")

    assert token

    client.cookies.delete(
        "carequeue_session",
        path="/api",
    )

    response = client.get(
        "/api/security/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required.",
    }


def test_logout_revokes_and_clears_session_cookie(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200
    assert client.cookies.get("carequeue_csrf")

    logout_response = client.post(
        "/api/security/logout",
        headers=csrf_headers(client),
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {
        "logged_out": True,
    }

    set_cookie = logout_response.headers["set-cookie"]

    assert "carequeue_session=" in set_cookie
    assert "Max-Age=0" in set_cookie

    current_user_response = client.get("/api/security/me")

    assert current_user_response.status_code == 401

    assert client.cookies.get("carequeue_csrf") is None

    set_cookie_headers = logout_response.headers.get_list("set-cookie")
    csrf_cookie_header = next(
        header for header in set_cookie_headers if header.startswith("carequeue_csrf=")
    )

    assert "Max-Age=0" in csrf_cookie_header
    assert "Path=/" in csrf_cookie_header


def test_admin_can_list_users(client):
    create_user("admin@example.com", "correct horse battery staple", role="Admin")
    create_user("ur@example.com", "correct horse battery staple", role="UR")

    response = client.get(
        "/api/security/users",
        headers=auth_headers_for(
            client,
            "admin@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert [user["username"] for user in data["users"]] == [
        "admin@example.com",
        "ur@example.com",
    ]
    assert "password_hash" not in data["users"][0]


def test_ur_user_cannot_list_users(client):
    create_user("ur@example.com", "correct horse battery staple", role="UR")

    response = client.get(
        "/api/security/users",
        headers=auth_headers_for(
            client,
            "ur@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 403


def test_setup_initial_admin_status_is_available_when_no_users_exist(client):
    response = client.get("/api/security/setup-initial-admin/status")

    assert response.status_code == 200
    assert response.json() == {"setup_available": True}


def test_setup_initial_admin_status_is_unavailable_after_user_exists(client):
    create_user("existing@example.com", "correct horse battery staple", role="Admin")

    response = client.get("/api/security/setup-initial-admin/status")

    assert response.status_code == 200
    assert response.json() == {"setup_available": False}


def test_setup_initial_admin_status_rejects_non_loopback_client():
    with TestClient(
        create_app(),
        client=("203.0.113.10", 50000),
    ) as remote_client:
        response = remote_client.get("/api/security/setup-initial-admin/status")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Initial admin setup must be completed from the local machine."
    }


def test_setup_initial_admin_rejects_non_loopback_client():
    with TestClient(
        create_app(),
        client=("203.0.113.10", 50000),
    ) as remote_client:
        response = remote_client.post(
            "/api/security/setup-initial-admin",
            json={
                "username": "admin@example.com",
                "password": "correct horse battery staple",
            },
        )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Initial admin setup must be completed from the local machine."
    }


def test_admin_can_create_user_with_generated_temporary_password(client):
    create_user("admin@example.com", "correct horse battery staple", role="Admin")

    response = client.post(
        "/api/security/users",
        json={
            "username": "new-user@example.com",
            "role": "Read Only",
        },
        headers=auth_headers_for(
            client,
            "admin@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 201

    data = response.json()
    created_user = data["user"]

    assert created_user["username"] == "new-user@example.com"
    assert created_user["role"] == "Read Only"
    assert created_user["is_active"] is True
    assert created_user["must_change_password"] is True
    assert len(data["temporary_password"]) == 24
    assert "password_hash" not in created_user

    login_response = client.post(
        "/api/security/login",
        json={
            "username": created_user["username"],
            "password": data["temporary_password"],
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["must_change_password"] is True


def test_create_user_writes_safe_audit_event(client):
    create_user("admin@example.com", "correct horse battery staple", role="Admin")

    response = client.post(
        "/api/security/users",
        json={
            "username": "new-user@example.com",
            "role": "UR",
        },
        headers=auth_headers_for(
            client,
            "admin@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 201

    temporary_password = response.json()["temporary_password"]
    created_user = response.json()["user"]

    with get_conn() as conn:
        row = conn.execute("""
            SELECT action, resource_type, resource_id, metadata
            FROM audit_events
            WHERE action = 'user.create'
            """).fetchone()

    assert row["action"] == "user.create"
    assert row["resource_type"] == "user"
    assert row["resource_id"] == created_user["id"]
    assert temporary_password not in row["metadata"]
    assert "new-user@example.com" not in row["metadata"]
    assert "must_change_password" in row["metadata"]


def test_create_user_rejects_admin_supplied_password(client):
    create_user("admin@example.com", "correct horse battery staple", role="Admin")

    response = client.post(
        "/api/security/users",
        json={
            "username": "new-user@example.com",
            "password": "admin selected password",
            "role": "UR",
        },
        headers=auth_headers_for(
            client,
            "admin@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 422


def test_admin_can_update_user_role_and_active_status(client):
    admin = create_user(
        "admin@example.com", "correct horse battery staple", role="Admin"
    )
    user = create_user("user@example.com", "correct horse battery staple", role="UR")

    response = client.patch(
        f"/api/security/users/{user['id']}",
        json={
            "role": "Read Only",
            "is_active": False,
        },
        headers=auth_headers_for(
            client,
            admin["username"],
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["role"] == "Read Only"
    assert data["is_active"] is False


def test_update_user_writes_audit_event_without_sensitive_values(client):
    admin = create_user(
        "admin@example.com", "correct horse battery staple", role="Admin"
    )
    user = create_user("user@example.com", "correct horse battery staple", role="UR")

    response = client.patch(
        f"/api/security/users/{user['id']}",
        json={"role": "Read Only"},
        headers=auth_headers_for(
            client,
            admin["username"],
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 200

    with get_conn() as conn:
        row = conn.execute("""
            SELECT action, metadata
            FROM audit_events
            WHERE action = 'user.update'
            """).fetchone()

    assert row["action"] == "user.update"
    assert "role" in row["metadata"]
    assert "user@example.com" not in row["metadata"]
    assert "correct horse battery staple" not in row["metadata"]


def test_admin_cannot_remove_own_admin_access(client):
    admin = create_user(
        "admin@example.com", "correct horse battery staple", role="Admin"
    )

    response = client.patch(
        f"/api/security/users/{admin['id']}",
        json={"role": "UR"},
        headers=auth_headers_for(
            client,
            admin["username"],
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Admins cannot remove their own admin access.",
    }


def test_admin_can_list_audit_events(client):
    admin = create_user(
        "admin@example.com", "correct horse battery staple", role="Admin"
    )

    headers = auth_headers_for(
        client,
        admin["username"],
        "correct horse battery staple",
    )

    response = client.get(
        "/api/security/audit-events?page=1&page_size=10",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total"] >= 1
    assert isinstance(data["events"], list)


def test_ur_user_cannot_list_audit_events(client):
    create_user("ur@example.com", "correct horse battery staple", role="UR")

    response = client.get(
        "/api/security/audit-events",
        headers=auth_headers_for(
            client,
            "ur@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 403


def test_audit_events_endpoint_supports_action_filter(client):
    admin = create_user(
        "admin@example.com", "correct horse battery staple", role="Admin"
    )

    headers = auth_headers_for(
        client,
        admin["username"],
        "correct horse battery staple",
    )

    response = client.get(
        "/api/security/audit-events?action=login",
        headers=headers,
    )

    assert response.status_code == 200

    events = response.json()["events"]

    assert events
    assert all(event["action"] == "security.login" for event in events)


def test_audit_events_endpoint_supports_partial_username_filter(client):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    create_user(
        "readonly@example.com",
        "correct horse battery staple",
        role="Read Only",
    )

    readonly_headers = auth_headers_for(
        client,
        "readonly@example.com",
        "correct horse battery staple",
    )

    client.post("/api/security/logout", headers=readonly_headers)

    response = client.get(
        "/api/security/audit-events?username=read",
        headers=auth_headers_for(
            client,
            admin["username"],
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 200

    events = response.json()["events"]

    assert events
    assert all(event["username"] == "readonly@example.com" for event in events)


def test_update_user_returns_404_for_missing_user(client):
    create_user("admin@example.com", "correct horse battery staple", role="Admin")

    response = client.patch(
        "/api/security/users/999",
        json={"role": "UR"},
        headers=auth_headers_for(
            client,
            "admin@example.com",
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 404


def test_me_rejects_missing_token(client):
    response = client.get("/api/security/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_me_rejects_invalid_token(client):
    response = client.get(
        "/api/security/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_logout_revokes_session(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    logout_response = client.post(
        "/api/security/logout",
        headers=csrf_headers(client),
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {"logged_out": True}

    me_response = client.get("/api/security/me")

    assert me_response.status_code == 401


def test_user_can_change_own_password(client):
    create_user(
        "user@example.com",
        "old password value",
        role="UR",
    )

    headers = auth_headers_for(
        client,
        "user@example.com",
        "old password value",
    )

    response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "old password value",
            "new_password": "new password value",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["password_changed"] is True
    assert response.json()["sessions_revoked"] >= 1

    old_login = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "old password value",
        },
    )
    new_login = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "new password value",
        },
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200
    assert new_login.json()["user"]["must_change_password"] is False


def test_change_password_rejects_short_new_password(client):
    create_user(
        "user@example.com",
        "old password value",
        role="UR",
    )

    response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "old password value",
            "new_password": "short",
        },
        headers=auth_headers_for(
            client,
            "user@example.com",
            "old password value",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Password must be at least 12 characters.",
    }


def test_change_password_rejects_incorrect_current_password(client):
    create_user(
        "user@example.com",
        "old password value",
        role="UR",
    )

    response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "wrong password",
            "new_password": "new password value",
        },
        headers=auth_headers_for(
            client,
            "user@example.com",
            "old password value",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Current password is incorrect.",
    }


def test_change_password_clears_forced_change_state(client):
    create_user(
        "temporary@example.com",
        "temporary password value",
        role="UR",
        must_change_password=True,
    )

    response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "temporary password value",
            "new_password": "permanent password value",
        },
        headers=auth_headers_for(
            client,
            "temporary@example.com",
            "temporary password value",
        ),
    )

    assert response.status_code == 200

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "temporary@example.com",
            "password": "permanent password value",
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["must_change_password"] is False


def test_change_password_revokes_current_session(client):
    user = create_user(
        "user@example.com",
        "old password value",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": "old password value",
        },
    )

    assert login_response.status_code == 200

    session_token = client.cookies.get("carequeue_session")

    assert session_token

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "old password value",
            "new_password": "new password value",
        },
        headers={
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 200

    client.cookies.set(
        "carequeue_session",
        session_token,
        path="/api",
    )

    me_response = client.get("/api/security/me")

    assert me_response.status_code == 401


def test_admin_reset_returns_temporary_password_once(client):
    admin = create_user(
        "admin@example.com",
        "admin password value",
        role="Admin",
    )
    user = create_user(
        "user@example.com",
        "old password value",
        role="UR",
    )

    response = client.post(
        f"/api/security/users/{user['id']}/reset-password",
        headers=auth_headers_for(
            client,
            admin["username"],
            "admin password value",
        ),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["password_reset"] is True
    assert data["must_change_password"] is True
    assert data["sessions_revoked"] >= 0
    assert len(data["temporary_password"]) == 24

    old_login = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": "old password value",
        },
    )
    temporary_login = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": data["temporary_password"],
        },
    )

    assert old_login.status_code == 401
    assert temporary_login.status_code == 200
    assert temporary_login.json()["user"]["must_change_password"] is True


def test_admin_reset_revokes_existing_user_sessions(client):
    admin = create_user(
        "admin@example.com",
        "admin password value",
        role="Admin",
    )
    user = create_user(
        "user@example.com",
        "old password value",
        role="UR",
    )

    user_login = client.post(
        "/api/security/login",
        json={
            "username": user["username"],
            "password": "old password value",
        },
    )
    assert user_login.status_code == 200

    user_token = client.cookies.get("carequeue_session")

    assert user_token

    response = client.post(
        f"/api/security/users/{user['id']}/reset-password",
        headers=auth_headers_for(
            client,
            admin["username"],
            "admin password value",
        ),
    )

    assert response.status_code == 200

    client.cookies.set(
        "carequeue_session",
        user_token,
        path="/api",
    )

    previous_session = client.get("/api/security/me")

    assert previous_session.status_code == 401


def test_ur_user_cannot_reset_passwords(client):
    first_user = create_user(
        "first@example.com",
        "password value",
        role="UR",
    )
    second_user = create_user(
        "second@example.com",
        "password value",
        role="UR",
    )

    response = client.post(
        f"/api/security/users/{second_user['id']}/reset-password",
        headers=auth_headers_for(
            client,
            first_user["username"],
            "password value",
        ),
    )

    assert response.status_code == 403


def test_admin_cannot_use_reset_endpoint_for_self(client):
    admin = create_user(
        "admin@example.com",
        "password value",
        role="Admin",
    )

    response = client.post(
        f"/api/security/users/{admin['id']}/reset-password",
        headers=auth_headers_for(
            client,
            admin["username"],
            "password value",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Use change password to update your own password.",
    }


def test_password_reset_audit_event_does_not_store_temporary_password(client):
    admin = create_user(
        "admin@example.com",
        "admin password value",
        role="Admin",
    )
    user = create_user(
        "user@example.com",
        "old password value",
        role="UR",
    )

    response = client.post(
        f"/api/security/users/{user['id']}/reset-password",
        headers=auth_headers_for(
            client,
            admin["username"],
            "admin password value",
        ),
    )

    assert response.status_code == 200

    temporary_password = response.json()["temporary_password"]

    with get_conn() as conn:
        row = conn.execute("""
            SELECT action, resource_id, metadata
            FROM audit_events
            WHERE action = 'user.password_reset'
            """).fetchone()

    assert row is not None
    assert row["resource_id"] == user["id"]
    assert temporary_password not in row["metadata"]


def test_admin_can_reset_user_mfa(client):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    secret = pyotp.random_base32()

    assert store_user_mfa_secret(user["id"], secret) is True
    assert enable_user_mfa(user["id"]) is True

    response = client.post(
        f"/api/security/users/{user['id']}/reset-mfa",
        headers=auth_headers_for(
            client,
            admin["username"],
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 200
    assert response.json() == {
        "mfa_reset": True,
        "sessions_revoked": 0,
        "mfa_enabled": False,
    }

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT mfa_enabled, mfa_secret
            FROM users
            WHERE id = ?
            """,
            (user["id"],),
        ).fetchone()

    assert row is not None
    assert row["mfa_enabled"] == 0
    assert row["mfa_secret"] is None


def test_admin_mfa_reset_revokes_target_user_sessions(client):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    user_headers = auth_headers_for(
        client,
        user["username"],
        "correct horse battery staple",
    )

    assert user_headers

    admin_headers = auth_headers_for(
        client,
        admin["username"],
        "correct horse battery staple",
    )

    response = client.post(
        f"/api/security/users/{user['id']}/reset-mfa",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["sessions_revoked"] == 1

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM sessions
            WHERE user_id = ?
            AND revoked_at IS NOT NULL
            """,
            (user["id"],),
        ).fetchone()

    assert row is not None
    assert row["count"] == 1


def test_admin_cannot_reset_own_mfa_from_user_management(client):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    response = client.post(
        f"/api/security/users/{admin['id']}/reset-mfa",
        headers=auth_headers_for(
            client,
            admin["username"],
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Admins cannot reset their own MFA from user management.",
    }


def test_reset_user_mfa_requires_admin(client):
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )
    target_user = create_user(
        "target@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        f"/api/security/users/{target_user['id']}/reset-mfa",
        headers=auth_headers_for(
            client,
            user["username"],
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Operation not permitted for this role.",
    }


def test_reset_user_mfa_writes_safe_audit_event(client):
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    user = create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    secret = pyotp.random_base32()

    assert store_user_mfa_secret(user["id"], secret) is True
    assert enable_user_mfa(user["id"]) is True

    response = client.post(
        f"/api/security/users/{user['id']}/reset-mfa",
        headers=auth_headers_for(
            client,
            admin["username"],
            "correct horse battery staple",
        ),
    )

    assert response.status_code == 200

    with get_conn() as conn:
        row = conn.execute("""
            SELECT action, metadata
            FROM audit_events
            WHERE action = 'user.mfa_reset'
            """).fetchone()

    assert row is not None
    assert row["action"] == "user.mfa_reset"
    assert secret not in row["metadata"]
    assert "user@example.com" not in row["metadata"]
    assert "sessions_revoked" in row["metadata"]


def test_login_and_logout_write_audit_events(client):
    create_user("user@example.com", "correct horse battery staple", role="UR")

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    logout_response = client.post(
        "/api/security/logout",
        headers=csrf_headers(client),
    )

    assert logout_response.status_code == 200

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT action, username
            FROM audit_events
            ORDER BY id
            """).fetchall()

    assert [(row["action"], row["username"]) for row in rows] == [
        ("security.login", "user@example.com"),
        ("security.logout", "user@example.com"),
    ]


def test_forced_change_user_can_access_me(client):
    user = create_user(
        "temporary@example.com",
        "temporary password value",
        role="UR",
        must_change_password=True,
    )

    headers = auth_headers_for(
        client,
        user["username"],
        "temporary password value",
    )

    response = client.get(
        "/api/security/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["user"]["must_change_password"] is True


def test_forced_change_user_can_log_out(client):
    user = create_user(
        "temporary@example.com",
        "temporary password value",
        role="UR",
        must_change_password=True,
    )

    auth_headers_for(
        client,
        user["username"],
        "temporary password value",
    )

    response = client.post(
        "/api/security/logout",
        headers=csrf_headers(client),
    )

    assert response.status_code == 200
    assert response.json() == {"logged_out": True}

    me_response = client.get("/api/security/me")

    assert me_response.status_code == 401


def test_forced_change_admin_cannot_access_admin_routes(client):
    admin = create_user(
        "temporary-admin@example.com",
        "temporary password value",
        role="Admin",
        must_change_password=True,
    )

    response = client.get(
        "/api/security/users",
        headers=auth_headers_for(
            client,
            admin["username"],
            "temporary password value",
        ),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Password change required.",
    }


def test_forced_change_admin_cannot_access_audit_events(client):
    admin = create_user(
        "temporary-admin@example.com",
        "temporary password value",
        role="Admin",
        must_change_password=True,
    )

    response = client.get(
        "/api/security/audit-events",
        headers=auth_headers_for(
            client,
            admin["username"],
            "temporary password value",
        ),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Password change required.",
    }


def test_forced_change_user_can_change_password(client):
    user = create_user(
        "temporary@example.com",
        "temporary password value",
        role="UR",
        must_change_password=True,
    )

    response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "temporary password value",
            "new_password": "permanent password value",
        },
        headers=auth_headers_for(
            client,
            user["username"],
            "temporary password value",
        ),
    )

    assert response.status_code == 200
    assert response.json()["password_changed"] is True


def test_user_regains_protected_access_after_required_password_change(client):
    admin = create_user(
        "temporary-admin@example.com",
        "temporary password value",
        role="Admin",
        must_change_password=True,
    )

    temporary_headers = auth_headers_for(
        client,
        admin["username"],
        "temporary password value",
    )

    blocked_response = client.get(
        "/api/security/users",
        headers=temporary_headers,
    )

    assert blocked_response.status_code == 403
    assert blocked_response.json() == {
        "detail": "Password change required.",
    }

    change_response = client.post(
        "/api/security/change-password",
        json={
            "current_password": "temporary password value",
            "new_password": "permanent password value",
        },
        headers=temporary_headers,
    )

    assert change_response.status_code == 200

    permanent_headers = auth_headers_for(
        client,
        admin["username"],
        "permanent password value",
    )

    allowed_response = client.get(
        "/api/security/users",
        headers=permanent_headers,
    )

    assert allowed_response.status_code == 200
    assert allowed_response.json()["users"][0]["must_change_password"] is False


def test_me_returns_same_session_expiration_as_login(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    login_expiration = login_response.json()["session"]["expires_at"]

    assert login_expiration

    me_response = client.get("/api/security/me")

    assert me_response.status_code == 200
    assert me_response.json()["session"]["expires_at"] == login_expiration


def test_user_can_renew_active_session(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    original_expiration = login_response.json()["session"]["expires_at"]

    original_session_cookie = client.cookies.get("carequeue_session")
    original_csrf_cookie = client.cookies.get("carequeue_csrf")

    assert original_session_cookie
    assert original_csrf_cookie

    renew_response = client.post(
        "/api/security/session/renew",
        headers=csrf_headers(client),
    )

    assert renew_response.status_code == 200

    renewed_expiration = renew_response.json()["expires_at"]

    assert renewed_expiration >= original_expiration

    renewed_session_cookie = client.cookies.get("carequeue_session")
    renewed_csrf_cookie = client.cookies.get("carequeue_csrf")

    assert renewed_session_cookie
    assert renewed_csrf_cookie
    assert renewed_session_cookie != original_session_cookie
    assert renewed_csrf_cookie != original_csrf_cookie

    set_cookie_headers = renew_response.headers.get_list("set-cookie")

    assert any(
        header.startswith("carequeue_session=") and "Max-Age=1200" in header
        for header in set_cookie_headers
    )
    assert any(
        header.startswith("carequeue_csrf=") and "Max-Age=1200" in header
        for header in set_cookie_headers
    )


def test_session_renewal_requires_csrf_header(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    response = client.post(
        "/api/security/session/renew",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "CSRF validation failed.",
    }


def test_session_renewal_requires_active_session(client):
    response = client.post(
        "/api/security/session/renew",
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required.",
    }


def test_me_returns_renewed_session_expiration(client):
    create_user(
        "user@example.com",
        "correct horse battery staple",
        role="UR",
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "user@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    renew_response = client.post(
        "/api/security/session/renew",
        headers=csrf_headers(client),
    )

    assert renew_response.status_code == 200

    renewed_expiration = renew_response.json()["expires_at"]

    me_response = client.get("/api/security/me")

    assert me_response.status_code == 200
    assert me_response.json()["session"]["expires_at"] == renewed_expiration


def test_setup_initial_admin_creates_admin_when_no_users_exist(client):
    response = client.post(
        "/api/security/setup-initial-admin",
        json={
            "username": "FirstAdmin@Example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["setup_complete"] is True
    assert data["user"]["username"] == "firstadmin@example.com"
    assert data["user"]["role"] == "Admin"
    assert data["user"]["is_active"] is True
    assert data["user"]["must_change_password"] is False
    assert data["user"]["mfa_enabled"] is False

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "firstadmin@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200


def test_setup_initial_admin_is_disabled_after_user_exists(client):
    create_user("existing@example.com", "correct horse battery staple", role="Admin")

    response = client.post(
        "/api/security/setup-initial-admin",
        json={
            "username": "new-admin@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Initial admin setup is no longer available."}


def test_setup_initial_admin_rejects_short_password(client):
    response = client.post(
        "/api/security/setup-initial-admin",
        json={
            "username": "admin@example.com",
            "password": "too-short",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Password must be at least 12 characters."}
