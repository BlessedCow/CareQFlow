from __future__ import annotations

from datetime import timedelta

import pyotp
import pytest

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.auth_delete_challenges import (
    MAX_AUTH_DELETE_CHALLENGES_PER_WINDOW,
    MAX_AUTH_DELETE_FAILED_ATTEMPTS,
    AuthDeleteChallengeError,
    authorize_auth_delete_in_transaction,
    consume_auth_delete_challenge,
    create_auth_delete_challenge,
    find_auth_delete_totp_step,
    get_active_auth_delete_challenge,
    is_auth_delete_account_locked,
    record_failed_auth_delete_attempt,
    reserve_auth_delete_totp_step,
)
from authstatus_api.security.mappings import format_datetime
from authstatus_api.security.mfa import TOTP_INTERVAL_SECONDS
from authstatus_api.security.mfa_challenges import hash_mfa_challenge_token
from authstatus_api.security.sessions import utc_now
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_delete_challenge_settings(monkeypatch, tmp_path):
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


def test_create_auth_delete_challenge_binds_user_and_auth():
    user = create_user(
        "delete-challenge@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(
        user_id=user["id"],
        auth_id=42,
    )

    challenge = get_active_auth_delete_challenge(
        created["token"],
        user["id"],
        42,
    )

    assert challenge is not None
    assert challenge["id"] == created["id"]
    assert challenge["user_id"] == user["id"]
    assert challenge["auth_id"] == 42
    assert challenge["token_hash"] == hash_mfa_challenge_token(created["token"])
    assert challenge["token_hash"] != created["token"]


def test_delete_challenge_rejects_different_auth():
    user = create_user(
        "delete-challenge@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(user["id"], 42)

    assert (
        get_active_auth_delete_challenge(
            created["token"],
            user["id"],
            43,
        )
        is None
    )


def test_delete_challenge_rejects_different_user():
    first = create_user(
        "first-delete-admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    second = create_user(
        "second-delete-admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(first["id"], 42)

    assert (
        get_active_auth_delete_challenge(
            created["token"],
            second["id"],
            42,
        )
        is None
    )


def test_delete_challenge_rejects_invalid_token():
    user = create_user(
        "delete-challenge@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    assert (
        get_active_auth_delete_challenge(
            "invalid-token",
            user["id"],
            42,
        )
        is None
    )


def test_delete_challenge_can_only_be_consumed_once():
    user = create_user(
        "consume-delete@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(user["id"], 42)
    token = created["token"]

    assert consume_auth_delete_challenge(token, user["id"], 42)
    assert not consume_auth_delete_challenge(token, user["id"], 42)

    assert get_active_auth_delete_challenge(token, user["id"], 42) is None


def test_delete_challenge_cannot_be_consumed_for_different_auth():
    user = create_user(
        "scoped-delete@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(user["id"], 42)

    assert not consume_auth_delete_challenge(created["token"], user["id"], 43)

    assert (
        get_active_auth_delete_challenge(created["token"], user["id"], 42) is not None
    )


def test_failed_delete_attempts_invalidate_challenge():
    user = create_user(
        "failed-delete@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(user["id"], 42)
    token = created["token"]

    for _ in range(MAX_AUTH_DELETE_FAILED_ATTEMPTS - 1):
        assert record_failed_auth_delete_attempt(token, user["id"], 42)

    assert get_active_auth_delete_challenge(token, user["id"], 42) is not None

    assert record_failed_auth_delete_attempt(token, user["id"], 42)

    assert get_active_auth_delete_challenge(token, user["id"], 42) is None

    assert not consume_auth_delete_challenge(token, user["id"], 42)

    assert not record_failed_auth_delete_attempt(token, user["id"], 42)


def test_expired_delete_challenge_cannot_be_used():
    user = create_user(
        "expired-delete@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(user["id"], 42)
    token = created["token"]

    expired_at = format_datetime(utc_now() - timedelta(minutes=1))

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE auth_delete_challenges
            SET expires_at = ?
            WHERE id = ?
            """,
            (expired_at, created["id"]),
        )

    assert get_active_auth_delete_challenge(token, user["id"], 42) is None

    assert not consume_auth_delete_challenge(token, user["id"], 42)

    assert not record_failed_auth_delete_attempt(token, user["id"], 42)


def test_exhausted_delete_challenge_cannot_be_reactivated():
    user = create_user(
        "exhausted-delete@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(user["id"], 42)
    token = created["token"]

    for _ in range(MAX_AUTH_DELETE_FAILED_ATTEMPTS):
        assert record_failed_auth_delete_attempt(token, user["id"], 42)

    assert not consume_auth_delete_challenge(token, user["id"], 42)

    assert get_active_auth_delete_challenge(token, user["id"], 42) is None

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT failed_attempts, consumed_at
            FROM auth_delete_challenges
            WHERE id = ?
            """,
            (created["id"],),
        ).fetchone()

    assert row is not None
    assert row["failed_attempts"] == MAX_AUTH_DELETE_FAILED_ATTEMPTS
    assert row["consumed_at"] is not None


def test_auth_delete_totp_step_cannot_be_reused():
    user = create_user(
        "totp-replay@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    assert reserve_auth_delete_totp_step(user["id"], 123456)
    assert not reserve_auth_delete_totp_step(user["id"], 123456)

    assert reserve_auth_delete_totp_step(user["id"], 123457)


def test_auth_delete_totp_reservations_are_user_scoped():
    first = create_user(
        "totp-first@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    second = create_user(
        "totp-second@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    assert reserve_auth_delete_totp_step(first["id"], 123456)
    assert reserve_auth_delete_totp_step(second["id"], 123456)


def test_auth_delete_totp_reservation_rejects_negative_step():
    user = create_user(
        "totp-negative@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    assert not reserve_auth_delete_totp_step(user["id"], -1)


def test_delete_totp_step_matches_current_code():
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(
        secret,
        interval=TOTP_INTERVAL_SECONDS,
    )

    current_step = int(utc_now().timestamp() // TOTP_INTERVAL_SECONDS)

    code = totp.at(current_step * TOTP_INTERVAL_SECONDS)

    assert find_auth_delete_totp_step(secret, code) == current_step


def test_delete_totp_step_accepts_adjacent_interval():
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(
        secret,
        interval=TOTP_INTERVAL_SECONDS,
    )

    current_step = int(utc_now().timestamp() // TOTP_INTERVAL_SECONDS)

    previous_step = current_step - 1
    code = totp.at(previous_step * TOTP_INTERVAL_SECONDS)

    assert find_auth_delete_totp_step(secret, code) == previous_step


def test_delete_totp_step_rejects_invalid_code():
    secret = pyotp.random_base32()

    assert find_auth_delete_totp_step(secret, "abcdef") is None
    assert find_auth_delete_totp_step(secret, "12345") is None
    assert find_auth_delete_totp_step(secret, "1234567") is None
    assert find_auth_delete_totp_step(secret, "１２３４５６") is None


def test_transactional_delete_authorization_succeeds():
    user = create_user(
        "atomic-delete@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    created = create_auth_delete_challenge(user["id"], 42)

    with get_conn() as conn:
        authorize_auth_delete_in_transaction(
            conn,
            token=created["token"],
            user_id=user["id"],
            auth_id=42,
            time_step=123456,
        )

    assert get_active_auth_delete_challenge(created["token"], user["id"], 42) is None

    assert not reserve_auth_delete_totp_step(user["id"], 123456)


def test_transactional_delete_authorization_rejects_totp_replay():
    user = create_user(
        "replay-delete@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    first = create_auth_delete_challenge(user["id"], 42)
    second = create_auth_delete_challenge(user["id"], 43)

    with get_conn() as conn:
        authorize_auth_delete_in_transaction(
            conn,
            token=first["token"],
            user_id=user["id"],
            auth_id=42,
            time_step=123456,
        )

    with pytest.raises(
        AuthDeleteChallengeError,
        match="already been used",
    ):
        with get_conn() as conn:
            authorize_auth_delete_in_transaction(
                conn,
                token=second["token"],
                user_id=user["id"],
                auth_id=43,
                time_step=123456,
            )

    assert get_active_auth_delete_challenge(second["token"], user["id"], 43) is not None


def test_transactional_delete_authorization_rolls_back():
    user = create_user(
        "rollback-delete@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    created = create_auth_delete_challenge(user["id"], 42)

    with pytest.raises(RuntimeError, match="Simulated failure"):
        with get_conn() as conn:
            authorize_auth_delete_in_transaction(
                conn,
                token=created["token"],
                user_id=user["id"],
                auth_id=42,
                time_step=123456,
            )

            raise RuntimeError("Simulated failure")

    assert (
        get_active_auth_delete_challenge(created["token"], user["id"], 42) is not None
    )

    assert reserve_auth_delete_totp_step(user["id"], 123456)


def test_delete_challenge_issuance_is_rate_limited():
    user = create_user(
        "limited-delete-admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    for auth_id in range(
        1,
        MAX_AUTH_DELETE_CHALLENGES_PER_WINDOW + 1,
    ):
        created = create_auth_delete_challenge(
            user["id"],
            auth_id,
        )
        assert created["token"]

    with pytest.raises(
        AuthDeleteChallengeError,
        match="Too many authorization deletion challenges",
    ):
        create_auth_delete_challenge(user["id"], 99)


def test_delete_challenge_issuance_limit_is_user_scoped():
    first = create_user(
        "limited-first@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    second = create_user(
        "limited-second@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    for _ in range(MAX_AUTH_DELETE_CHALLENGES_PER_WINDOW):
        create_auth_delete_challenge(first["id"], 42)

    with pytest.raises(AuthDeleteChallengeError):
        create_auth_delete_challenge(first["id"], 43)

    created = create_auth_delete_challenge(second["id"], 42)

    assert created["token"]


def test_delete_challenge_issuance_window_expires():
    user = create_user(
        "expired-issuance@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    for _ in range(MAX_AUTH_DELETE_CHALLENGES_PER_WINDOW):
        create_auth_delete_challenge(user["id"], 42)

    old_timestamp = format_datetime(utc_now() - timedelta(minutes=20))

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE auth_delete_challenges
            SET created_at = ?
            WHERE user_id = ?
            """,
            (old_timestamp, user["id"]),
        )

    created = create_auth_delete_challenge(user["id"], 42)

    assert created["token"]


def test_account_failed_attempts_accumulate_across_challenges():
    user = create_user(
        "account-limit@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    first = create_auth_delete_challenge(user["id"], 42)
    second = create_auth_delete_challenge(user["id"], 43)

    for _ in range(3):
        assert record_failed_auth_delete_attempt(first["token"], user["id"], 42)

    for _ in range(2):
        assert record_failed_auth_delete_attempt(second["token"], user["id"], 43)

    assert not record_failed_auth_delete_attempt(second["token"], user["id"], 43)


def test_account_failed_attempt_limit_is_user_scoped():
    first_user = create_user(
        "limited-account@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    second_user = create_user(
        "unlimited-account@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    first = create_auth_delete_challenge(first_user["id"], 42)
    second = create_auth_delete_challenge(second_user["id"], 42)

    for _ in range(5):
        assert record_failed_auth_delete_attempt(first["token"], first_user["id"], 42)

    assert record_failed_auth_delete_attempt(second["token"], second_user["id"], 42)


def test_account_lockout_blocks_other_challenges():
    user = create_user(
        "lockout-admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    first = create_auth_delete_challenge(user["id"], 42)
    second = create_auth_delete_challenge(user["id"], 43)

    for _ in range(MAX_AUTH_DELETE_FAILED_ATTEMPTS):
        assert record_failed_auth_delete_attempt(first["token"], user["id"], 42)

    assert is_auth_delete_account_locked(user["id"])

    assert get_active_auth_delete_challenge(second["token"], user["id"], 43) is None

    with pytest.raises(
        AuthDeleteChallengeError,
        match="temporarily locked",
    ):
        create_auth_delete_challenge(user["id"], 44)


def test_account_lockout_expires_after_failure_window():
    user = create_user(
        "expired-lockout@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    created = create_auth_delete_challenge(user["id"], 42)

    for _ in range(MAX_AUTH_DELETE_FAILED_ATTEMPTS):
        assert record_failed_auth_delete_attempt(created["token"], user["id"], 42)

    assert is_auth_delete_account_locked(user["id"])

    old_timestamp = format_datetime(utc_now() - timedelta(minutes=20))

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE auth_delete_failed_attempts
            SET attempted_at = ?
            WHERE user_id = ?
            """,
            (old_timestamp, user["id"]),
        )

    assert not is_auth_delete_account_locked(user["id"])

    new_challenge = create_auth_delete_challenge(user["id"], 43)

    assert new_challenge["token"]
