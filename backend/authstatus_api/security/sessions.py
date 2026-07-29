from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.security.mappings import (
    format_datetime,
    parse_datetime,
    session_row_to_dict,
)

SESSION_TOKEN_BYTES = 32
DEFAULT_SESSION_MINUTES = 20


def generate_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(UTC)


def session_expiration(minutes: int = DEFAULT_SESSION_MINUTES) -> datetime:
    return utc_now() + timedelta(minutes=minutes)


def is_session_expired(expires_at: datetime, now: datetime | None = None) -> bool:
    current_time = now or utc_now()
    return expires_at <= current_time


def create_user_session(
    user_id: int,
    *,
    minutes: int = DEFAULT_SESSION_MINUTES,
    ip_address: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    init_db()

    token = generate_session_token()
    token_hash = hash_session_token(token)
    now = format_datetime(utc_now())
    expires_at = format_datetime(session_expiration(minutes=minutes))

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sessions (
                user_id,
                token_hash,
                created_at,
                last_seen_at,
                expires_at,
                ip_address,
                user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                token_hash,
                now,
                now,
                expires_at,
                ip_address,
                user_agent,
            ),
        )

        session_id = cursor.lastrowid

    session = get_session_by_id(int(session_id))
    if session is None:
        raise RuntimeError("Unable to create session.")

    return {
        "token": token,
        "session": session,
    }


def get_session_by_id(session_id: int) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()

    return session_row_to_dict(row)


def get_active_session_by_token(token: str) -> dict[str, Any] | None:
    init_db()

    token_hash = hash_session_token(token)

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM sessions
            WHERE token_hash = ?
              AND revoked_at IS NULL
            """,
            (token_hash,),
        ).fetchone()

    session = session_row_to_dict(row)

    if session is None:
        return None

    if is_session_expired(parse_datetime(session["expires_at"])):
        return None

    return session


def touch_session(token: str) -> None:
    init_db()

    token_hash = hash_session_token(token)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET last_seen_at = ?
            WHERE token_hash = ?
              AND revoked_at IS NULL
            """,
            (now, token_hash),
        )


def renew_session(
    token: str,
    *,
    minutes: int = DEFAULT_SESSION_MINUTES,
) -> dict[str, Any] | None:
    init_db()

    current_token_hash = hash_session_token(token)
    renewed_token = generate_session_token()
    renewed_token_hash = hash_session_token(renewed_token)

    now_datetime = utc_now()
    now = format_datetime(now_datetime)
    expires_at = format_datetime(now_datetime + timedelta(minutes=minutes))

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE sessions
            SET
                token_hash = ?,
                last_seen_at = ?,
                expires_at = ?
            WHERE token_hash = ?
              AND revoked_at IS NULL
              AND expires_at > ?
            """,
            (
                renewed_token_hash,
                now,
                expires_at,
                current_token_hash,
                now,
            ),
        )

    if cursor.rowcount == 0:
        return None

    session = get_active_session_by_token(renewed_token)

    if session is None:
        raise RuntimeError("Unable to retrieve the renewed session.")

    return {
        "token": renewed_token,
        "session": session,
    }


def revoke_session(token: str) -> bool:
    init_db()

    token_hash = hash_session_token(token)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE sessions
            SET revoked_at = ?
            WHERE token_hash = ?
              AND revoked_at IS NULL
            """,
            (now, token_hash),
        )

    return cursor.rowcount > 0


def revoke_user_sessions(user_id: int) -> int:
    init_db()

    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE sessions
            SET revoked_at = ?
            WHERE user_id = ?
              AND revoked_at IS NULL
            """,
            (
                now,
                user_id,
            ),
        )

    return cursor.rowcount
