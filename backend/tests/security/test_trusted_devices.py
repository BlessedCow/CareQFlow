from __future__ import annotations

import string

import pytest

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.mappings import format_datetime
from authstatus_api.security.sessions import utc_now
from authstatus_api.security.trusted_devices import (
    create_trusted_device,
    get_active_trusted_device_by_token,
    hash_trusted_device_token,
    revoke_trusted_device,
    revoke_user_trusted_devices,
    touch_trusted_device,
)
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_trusted_device_test_settings(monkeypatch, tmp_path):
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


def test_hash_trusted_device_token_is_deterministic_hmac_sha256_hex():
    token = "trusted-device-token-value"

    first_hash = hash_trusted_device_token(token)
    second_hash = hash_trusted_device_token(token)

    assert first_hash == second_hash
    assert len(first_hash) == 64
    assert all(character in string.hexdigits for character in first_hash)
    assert first_hash != token


def test_hash_trusted_device_token_changes_when_token_changes():
    first_hash = hash_trusted_device_token("first-trusted-device-token")
    second_hash = hash_trusted_device_token("second-trusted-device-token")

    assert first_hash != second_hash


def test_trusted_device_can_be_retrieved_by_raw_token():
    user = create_user(
        "trusted-device@example.com",
        "correct horse battery staple",
        role="UR",
    )

    created = create_trusted_device(
        user["id"],
        ip_address="127.0.0.1",
        user_agent="CareQueue trusted-device test",
    )

    trusted_device = get_active_trusted_device_by_token(created["token"])

    assert trusted_device is not None
    assert trusted_device["id"] == created["trusted_device"]["id"]
    assert trusted_device["user_id"] == user["id"]
    assert trusted_device["token_hash"] == hash_trusted_device_token(created["token"])
    assert trusted_device["token_hash"] != created["token"]
    assert trusted_device["ip_address"] == "127.0.0.1"
    assert trusted_device["user_agent"] == "CareQueue trusted-device test"


def test_expired_trusted_device_is_not_active():
    user = create_user(
        "expired-trusted-device@example.com",
        "correct horse battery staple",
        role="UR",
    )
    created = create_trusted_device(user["id"])

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE trusted_devices
            SET expires_at = ?
            WHERE id = ?
            """,
            (
                "2020-01-01T00:00:00+00:00",
                created["trusted_device"]["id"],
            ),
        )

    assert get_active_trusted_device_by_token(created["token"]) is None


def test_touch_trusted_device_updates_last_used_at():
    user = create_user(
        "touched-trusted-device@example.com",
        "correct horse battery staple",
        role="UR",
    )
    created = create_trusted_device(user["id"])

    old_last_used_at = "2020-01-01T00:00:00+00:00"

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE trusted_devices
            SET last_used_at = ?
            WHERE id = ?
            """,
            (
                old_last_used_at,
                created["trusted_device"]["id"],
            ),
        )

    assert touch_trusted_device(created["token"]) is True

    trusted_device = get_active_trusted_device_by_token(created["token"])

    assert trusted_device is not None
    assert trusted_device["last_used_at"] != old_last_used_at
    assert trusted_device["last_used_at"] <= format_datetime(utc_now())


def test_revoke_trusted_device_prevents_future_use():
    user = create_user(
        "revoked-trusted-device@example.com",
        "correct horse battery staple",
        role="UR",
    )
    created = create_trusted_device(user["id"])

    assert revoke_trusted_device(created["token"]) is True
    assert get_active_trusted_device_by_token(created["token"]) is None
    assert revoke_trusted_device(created["token"]) is False


def test_revoke_user_trusted_devices_revokes_every_device():
    user = create_user(
        "revoke-all-trusted-devices@example.com",
        "correct horse battery staple",
        role="UR",
    )
    first_device = create_trusted_device(user["id"])
    second_device = create_trusted_device(user["id"])

    assert revoke_user_trusted_devices(user["id"]) == 2

    assert get_active_trusted_device_by_token(first_device["token"]) is None
    assert get_active_trusted_device_by_token(second_device["token"]) is None
