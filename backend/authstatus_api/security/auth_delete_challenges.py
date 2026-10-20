from __future__ import annotations

import hmac
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pyotp

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.security.mappings import format_datetime
from authstatus_api.security.mfa import (
    TOTP_DIGITS,
    TOTP_INTERVAL_SECONDS,
)
from authstatus_api.security.mfa_challenges import (
    generate_mfa_challenge_token,
    hash_mfa_challenge_token,
)
from authstatus_api.security.sessions import utc_now

AUTH_DELETE_CHALLENGE_MINUTES = 5
MAX_AUTH_DELETE_FAILED_ATTEMPTS = 5
AUTH_DELETE_FAILURE_WINDOW_MINUTES = 15
MAX_AUTH_DELETE_ACCOUNT_FAILURES = 5
AUTH_DELETE_ISSUANCE_WINDOW_MINUTES = 15
MAX_AUTH_DELETE_CHALLENGES_PER_WINDOW = 5


class AuthDeleteChallengeError(ValueError):
    pass


def create_auth_delete_challenge(
    user_id: int,
    auth_id: int,
) -> dict[str, Any]:
    init_db()

    if is_auth_delete_account_locked(user_id):
        raise AuthDeleteChallengeError(
            "Authorization deletion is temporarily locked due to repeated MFA failures."
        )

    token = generate_mfa_challenge_token()
    token_hash = hash_mfa_challenge_token(token)

    now = utc_now()
    created_at = format_datetime(now)
    expires_at = format_datetime(now + timedelta(minutes=AUTH_DELETE_CHALLENGE_MINUTES))
    window_start = format_datetime(
        now - timedelta(minutes=AUTH_DELETE_ISSUANCE_WINDOW_MINUTES)
    )

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO auth_delete_challenges (
                user_id,
                auth_id,
                token_hash,
                created_at,
                expires_at
            )
            SELECT ?, ?, ?, ?, ?
            WHERE (
                SELECT COUNT(*)
                FROM auth_delete_challenges
                WHERE user_id = ?
                  AND created_at > ?
            ) < ?
            """,
            (
                user_id,
                auth_id,
                token_hash,
                created_at,
                expires_at,
                user_id,
                window_start,
                MAX_AUTH_DELETE_CHALLENGES_PER_WINDOW,
            ),
        )

        if cursor.rowcount != 1:
            raise AuthDeleteChallengeError(
                "Too many authorization deletion challenges. Try again later."
            )

        challenge_id = cursor.lastrowid

    return {
        "id": int(challenge_id),
        "token": token,
        "expires_at": expires_at,
    }


def is_auth_delete_account_locked(user_id: int) -> bool:
    init_db()

    window_start = format_datetime(
        utc_now() - timedelta(minutes=AUTH_DELETE_FAILURE_WINDOW_MINUTES)
    )

    with get_conn() as conn:
        count = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM auth_delete_failed_attempts
            WHERE user_id = ?
              AND attempted_at > ?
            """,
            (user_id, window_start),
        ).fetchone()["total"]

    return count >= MAX_AUTH_DELETE_ACCOUNT_FAILURES


def get_active_auth_delete_challenge(
    token: str,
    user_id: int,
    auth_id: int,
) -> dict[str, Any] | None:
    init_db()

    if is_auth_delete_account_locked(user_id):
        return None

    token_hash = hash_mfa_challenge_token(token)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM auth_delete_challenges
            WHERE token_hash = ?
              AND user_id = ?
              AND auth_id = ?
              AND consumed_at IS NULL
              AND failed_attempts < ?
              AND expires_at > ?
            """,
            (
                token_hash,
                user_id,
                auth_id,
                MAX_AUTH_DELETE_FAILED_ATTEMPTS,
                now,
            ),
        ).fetchone()

    return dict(row) if row is not None else None


def record_failed_auth_delete_attempt(
    token: str,
    user_id: int,
    auth_id: int,
    *,
    on_recorded: Callable[[Any, bool], None] | None = None,
) -> bool:
    init_db()

    token_hash = hash_mfa_challenge_token(token)
    now = utc_now()
    attempted_at = format_datetime(now)
    window_start = format_datetime(
        now - timedelta(minutes=AUTH_DELETE_FAILURE_WINDOW_MINUTES)
    )

    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute(
            """
            INSERT INTO auth_delete_failed_attempts (
                user_id,
                auth_id,
                challenge_id,
                attempted_at
            )
            SELECT ?, ?, id, ?
            FROM auth_delete_challenges
            WHERE token_hash = ?
              AND user_id = ?
              AND auth_id = ?
              AND consumed_at IS NULL
              AND failed_attempts < ?
              AND expires_at > ?
              AND (
                  SELECT COUNT(*)
                  FROM auth_delete_failed_attempts
                  WHERE user_id = ?
                    AND attempted_at > ?
              ) < ?
            """,
            (
                user_id,
                auth_id,
                attempted_at,
                token_hash,
                user_id,
                auth_id,
                MAX_AUTH_DELETE_FAILED_ATTEMPTS,
                attempted_at,
                user_id,
                window_start,
                MAX_AUTH_DELETE_ACCOUNT_FAILURES,
            ),
        )

        if cursor.rowcount != 1:
            return False

        cursor = conn.execute(
            """
            UPDATE auth_delete_challenges
            SET
                failed_attempts = failed_attempts + 1,
                consumed_at = CASE
                    WHEN failed_attempts + 1 >= ?
                    THEN ?
                    ELSE consumed_at
                END
            WHERE token_hash = ?
              AND user_id = ?
              AND auth_id = ?
              AND consumed_at IS NULL
              AND failed_attempts < ?
              AND expires_at > ?
            """,
            (
                MAX_AUTH_DELETE_FAILED_ATTEMPTS,
                attempted_at,
                token_hash,
                user_id,
                auth_id,
                MAX_AUTH_DELETE_FAILED_ATTEMPTS,
                attempted_at,
            ),
        )

        if cursor.rowcount != 1:
            raise AuthDeleteChallengeError(
                "Unable to record the failed authentication attempt."
            )

        failure_count = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM auth_delete_failed_attempts
            WHERE user_id = ?
              AND attempted_at > ?
            """,
            (user_id, window_start),
        ).fetchone()["total"]

        locked = failure_count == MAX_AUTH_DELETE_ACCOUNT_FAILURES

        if on_recorded is not None:
            on_recorded(conn, locked)

    return True


def consume_auth_delete_challenge(
    token: str,
    user_id: int,
    auth_id: int,
) -> bool:
    init_db()

    if is_auth_delete_account_locked(user_id):
        return False
    token_hash = hash_mfa_challenge_token(token)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE auth_delete_challenges
            SET consumed_at = ?
            WHERE token_hash = ?
              AND user_id = ?
              AND auth_id = ?
              AND consumed_at IS NULL
              AND failed_attempts < ?
              AND expires_at > ?
            """,
            (
                now,
                token_hash,
                user_id,
                auth_id,
                MAX_AUTH_DELETE_FAILED_ATTEMPTS,
                now,
            ),
        )

    return cursor.rowcount == 1


def reserve_auth_delete_totp_step(
    user_id: int,
    time_step: int,
) -> bool:
    if time_step < 0:
        return False

    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO auth_delete_totp_uses (
                user_id,
                time_step,
                used_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, time_step) DO NOTHING
            """,
            (
                user_id,
                time_step,
                format_datetime(utc_now()),
            ),
        )

        return cursor.rowcount == 1


def find_auth_delete_totp_step(
    secret: str,
    code: str,
) -> int | None:
    normalized_code = code.strip()

    if (
        len(normalized_code) != TOTP_DIGITS
        or not normalized_code.isascii()
        or not normalized_code.isdigit()
    ):
        return None

    totp = pyotp.TOTP(
        secret,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL_SECONDS,
    )

    current_step = int(utc_now().timestamp() // TOTP_INTERVAL_SECONDS)

    for step in (
        current_step - 1,
        current_step,
        current_step + 1,
    ):
        if step < 0:
            continue

        expected_code = totp.at(step * TOTP_INTERVAL_SECONDS)

        if hmac.compare_digest(normalized_code, expected_code):
            return step

    return None


def authorize_auth_delete_in_transaction(
    conn: Any,
    *,
    token: str,
    user_id: int,
    auth_id: int,
    time_step: int,
) -> None:
    if time_step < 0:
        raise AuthDeleteChallengeError("Invalid MFA verification.")

    window_start = format_datetime(
        utc_now() - timedelta(minutes=AUTH_DELETE_FAILURE_WINDOW_MINUTES)
    )

    failure_count = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM auth_delete_failed_attempts
        WHERE user_id = ?
          AND attempted_at > ?
        """,
        (user_id, window_start),
    ).fetchone()["total"]

    if failure_count >= MAX_AUTH_DELETE_ACCOUNT_FAILURES:
        raise AuthDeleteChallengeError(
            "Authorization deletion is temporarily locked due to repeated MFA failures."
        )

    now = format_datetime(utc_now())
    token_hash = hash_mfa_challenge_token(token)

    cursor = conn.execute(
        """
        UPDATE auth_delete_challenges
        SET consumed_at = ?
        WHERE token_hash = ?
          AND user_id = ?
          AND auth_id = ?
          AND consumed_at IS NULL
          AND failed_attempts < ?
          AND expires_at > ?
        """,
        (
            now,
            token_hash,
            user_id,
            auth_id,
            MAX_AUTH_DELETE_FAILED_ATTEMPTS,
            now,
        ),
    )

    if cursor.rowcount != 1:
        raise AuthDeleteChallengeError(
            "Invalid or expired authorization deletion challenge."
        )

    cursor = conn.execute(
        """
        INSERT INTO auth_delete_totp_uses (
            user_id,
            time_step,
            used_at
        )
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, time_step) DO NOTHING
        """,
        (user_id, time_step, now),
    )

    if cursor.rowcount != 1:
        raise AuthDeleteChallengeError(
            "This authentication code has already been used."
        )
