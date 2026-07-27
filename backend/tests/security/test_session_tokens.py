from __future__ import annotations

from datetime import UTC, datetime, timedelta

from authstatus_api.security.sessions import (
    generate_session_token,
    hash_session_token,
    is_session_expired,
    session_expiration,
)


def test_generate_session_token_returns_random_tokens():
    first_token = generate_session_token()
    second_token = generate_session_token()

    assert first_token
    assert second_token
    assert first_token != second_token


def test_hash_session_token_is_deterministic_sha256_hex():
    token = "session-token"

    first_hash = hash_session_token(token)
    second_hash = hash_session_token(token)

    assert first_hash == second_hash
    assert first_hash != token
    assert len(first_hash) == 64


def test_hash_session_token_changes_when_token_changes():
    first_hash = hash_session_token("first-token")
    second_hash = hash_session_token("second-token")

    assert first_hash != second_hash


def test_session_expiration_returns_future_datetime():
    expires_at = session_expiration(minutes=30)

    assert expires_at.tzinfo is UTC
    assert expires_at > datetime.now(UTC)


def test_is_session_expired_returns_true_for_past_expiration():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    expires_at = now - timedelta(seconds=1)

    assert is_session_expired(expires_at, now=now) is True


def test_is_session_expired_returns_false_for_future_expiration():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    expires_at = now + timedelta(seconds=1)

    assert is_session_expired(expires_at, now=now) is False