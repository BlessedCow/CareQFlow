from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.sessions import (
    create_user_session,
    get_active_session_by_token,
    hash_session_token,
    renew_session,
    replace_user_session,
    revoke_session,
    revoke_user_sessions,
    touch_session,
)
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(tmp_path / "auth_tracker.db"))
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_revoke_user_sessions_revokes_all_active_sessions():
    user = create_user(
        "revoke-all@example.com",
        "password value",
        role="UR",
    )
    first_session = create_user_session(user["id"])
    second_session = create_user_session(user["id"])

    revoked_count = revoke_user_sessions(user["id"])

    assert revoked_count == 2
    assert get_active_session_by_token(first_session["token"]) is None
    assert get_active_session_by_token(second_session["token"]) is None


def test_replace_user_session_revokes_existing_sessions_and_creates_one_active():
    user = create_user(
        "replace-session@example.com",
        "password value",
        role="UR",
    )
    first_session = create_user_session(user["id"])
    second_session = create_user_session(user["id"])

    replacement = replace_user_session(
        user["id"],
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert replacement["sessions_revoked"] == 2
    assert get_active_session_by_token(first_session["token"]) is None
    assert get_active_session_by_token(second_session["token"]) is None

    active_session = get_active_session_by_token(replacement["token"])

    assert active_session is not None
    assert active_session["id"] == replacement["session"]["id"]
    assert active_session["ip_address"] == "127.0.0.1"
    assert active_session["user_agent"] == "pytest"


def test_create_user_session_returns_raw_token_once_and_stores_hash():
    user = create_user("session@example.com", "password value", role="UR")

    created_session = create_user_session(
        user["id"],
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    token = created_session["token"]
    session = created_session["session"]

    assert token
    assert session["user_id"] == user["id"]
    assert session["token_hash"] == hash_session_token(token)
    assert session["token_hash"] != token
    assert session["ip_address"] == "127.0.0.1"
    assert session["user_agent"] == "pytest"


def test_get_active_session_by_token_returns_active_session():
    user = create_user("active@example.com", "password value", role="UR")
    created_session = create_user_session(user["id"])

    session = get_active_session_by_token(created_session["token"])

    assert session is not None
    assert session["id"] == created_session["session"]["id"]


def test_get_active_session_by_token_rejects_unknown_token():
    assert get_active_session_by_token("unknown-token") is None


def test_get_active_session_by_token_rejects_expired_session():
    user = create_user("expired@example.com", "password value", role="UR")
    created_session = create_user_session(user["id"])
    expired_at = (datetime.now(UTC) - timedelta(minutes=1)).isoformat(
        timespec="seconds"
    )

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET expires_at = ?
            WHERE id = ?
            """,
            (expired_at, created_session["session"]["id"]),
        )

    assert get_active_session_by_token(created_session["token"]) is None


def test_touch_session_updates_last_seen_at():
    user = create_user("touch@example.com", "password value", role="UR")
    created_session = create_user_session(user["id"])

    before = created_session["session"]["last_seen_at"]

    touch_session(created_session["token"])

    refreshed = get_active_session_by_token(created_session["token"])

    assert refreshed is not None
    assert refreshed["last_seen_at"] >= before


def test_renew_session_rotates_token_and_extends_expiration():
    user = create_user(
        "renew@example.com",
        "password value",
        role="UR",
    )
    created_session = create_user_session(
        user["id"],
        minutes=5,
    )
    original_token = created_session["token"]
    original_expiration = created_session["session"]["expires_at"]

    renewed = renew_session(
        original_token,
        minutes=30,
    )

    assert renewed is not None
    assert renewed["token"] != original_token
    assert renewed["session"]["expires_at"] > original_expiration
    assert (
        renewed["session"]["last_seen_at"] >= created_session["session"]["last_seen_at"]
    )

    assert get_active_session_by_token(original_token) is None
    assert get_active_session_by_token(renewed["token"]) == renewed["session"]


def test_renew_session_rejects_expired_session():
    user = create_user(
        "renew-expired@example.com",
        "password value",
        role="UR",
    )
    created_session = create_user_session(user["id"])
    expired_at = (datetime.now(UTC) - timedelta(minutes=1)).isoformat(
        timespec="seconds"
    )

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET expires_at = ?
            WHERE id = ?
            """,
            (
                expired_at,
                created_session["session"]["id"],
            ),
        )

    assert renew_session(created_session["token"]) is None


def test_renew_session_rejects_revoked_session():
    user = create_user(
        "renew-revoked@example.com",
        "password value",
        role="UR",
    )
    created_session = create_user_session(user["id"])

    assert revoke_session(created_session["token"]) is True
    assert renew_session(created_session["token"]) is None


def test_renew_session_rejects_unknown_token():
    assert renew_session("unknown-token") is None


def test_revoke_session_revokes_active_session():
    user = create_user("revoke@example.com", "password value", role="UR")
    created_session = create_user_session(user["id"])

    assert revoke_session(created_session["token"]) is True
    assert get_active_session_by_token(created_session["token"]) is None


def test_revoke_session_returns_false_for_unknown_token():
    assert revoke_session("unknown-token") is False
