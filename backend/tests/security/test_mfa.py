from __future__ import annotations

import pyotp
import pytest

from authstatus_api.crypto import ENCRYPTED_TEXT_PREFIX, generate_encryption_key
from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.mfa import (
    MFA_ISSUER_NAME,
    build_totp_provisioning_uri,
    clear_user_mfa,
    enable_user_mfa,
    generate_totp_secret,
    get_user_mfa_secret,
    store_user_mfa_secret,
    verify_totp_code,
)
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_mfa_test_settings(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_generate_totp_secret_creates_valid_base32_secret():
    secret = generate_totp_secret()

    assert secret
    assert pyotp.TOTP(secret).now().isdigit()


def test_build_totp_provisioning_uri_contains_careqflow_issuer():
    secret = generate_totp_secret()

    uri = build_totp_provisioning_uri(
        "User@Example.com",
        secret,
    )

    assert uri.startswith("otpauth://totp/")
    assert "CareQFlow" in uri
    assert "user%40example.com" in uri
    assert f"issuer={MFA_ISSUER_NAME}" in uri


def test_verify_totp_code_accepts_current_code():
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).now()

    assert verify_totp_code(secret, code) is True


def test_verify_totp_code_rejects_invalid_code():
    secret = generate_totp_secret()

    assert verify_totp_code(secret, "000000") is False


@pytest.mark.parametrize(
    "code",
    [
        "",
        "12345",
        "1234567",
        "abcdef",
        "12 3456",
    ],
)
def test_verify_totp_code_rejects_malformed_codes(code):
    secret = generate_totp_secret()

    assert verify_totp_code(secret, code) is False


def test_store_user_mfa_secret_encrypts_secret_at_rest():
    user = create_user(
        "mfa@example.com",
        "correct horse battery staple",
        role="UR",
    )
    secret = generate_totp_secret()

    stored = store_user_mfa_secret(user["id"], secret)

    assert stored is True

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
    assert row["mfa_secret"] != secret
    assert row["mfa_secret"].startswith(ENCRYPTED_TEXT_PREFIX)


def test_get_user_mfa_secret_decrypts_stored_secret():
    user = create_user(
        "decrypt-mfa@example.com",
        "correct horse battery staple",
        role="UR",
    )
    secret = generate_totp_secret()

    store_user_mfa_secret(user["id"], secret)

    assert get_user_mfa_secret(user["id"]) == secret


def test_enable_user_mfa_requires_stored_secret():
    user = create_user(
        "no-secret@example.com",
        "correct horse battery staple",
        role="UR",
    )

    assert enable_user_mfa(user["id"]) is False


def test_enable_user_mfa_enables_user_with_secret():
    user = create_user(
        "enable-mfa@example.com",
        "correct horse battery staple",
        role="UR",
    )

    store_user_mfa_secret(
        user["id"],
        generate_totp_secret(),
    )

    assert enable_user_mfa(user["id"]) is True

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


def test_clear_user_mfa_removes_secret_and_disables_mfa():
    user = create_user(
        "clear-mfa@example.com",
        "correct horse battery staple",
        role="UR",
    )

    store_user_mfa_secret(
        user["id"],
        generate_totp_secret(),
    )
    enable_user_mfa(user["id"])

    assert clear_user_mfa(user["id"]) is True

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
