from __future__ import annotations

import sqlite3
from typing import Any

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.security.mappings import format_datetime, user_row_to_dict
from authstatus_api.security.password_hashing import hash_password, verify_password
from authstatus_api.security.password_policy import validate_password_policy
from authstatus_api.security.sessions import (
    get_active_session_by_token,
    touch_session,
    utc_now,
)


def create_user(
    username: str,
    password: str,
    role: str = "UR",
    *,
    must_change_password: bool = False,
) -> dict[str, Any]:
    init_db()

    validate_password_policy(password)

    normalized_username = username.strip().lower()
    now = format_datetime(utc_now())
    password_hash = hash_password(password)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                password_changed_at,
                must_change_password,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_username,
                password_hash,
                role,
                now,
                1 if must_change_password else 0,
                now,
                now,
            ),
        )

        user_id = cursor.lastrowid

    user = get_user_by_id(int(user_id))
    if user is None:
        raise RuntimeError("Unable to create user.")

    return user


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    return user_row_to_dict(row)


def get_user_by_username(username: str) -> dict[str, Any] | None:
    init_db()

    normalized_username = username.strip().lower()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (normalized_username,),
        ).fetchone()

    return user_row_to_dict(row)


def user_exists() -> bool:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM users
            LIMIT 1
            """,
        ).fetchone()

    return row is not None


def list_users() -> list[dict[str, Any]]:
    init_db()

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT *
            FROM users
            ORDER BY username
            """).fetchall()

    return [user_row_to_dict(row) for row in rows if row is not None]


def update_user(
    user_id: int,
    *,
    role: str | None = None,
    is_active: bool | None = None,
) -> dict[str, Any] | None:
    init_db()

    now = format_datetime(utc_now())

    try:
        with get_conn() as conn:
            if role is not None and is_active is not None:
                cursor = conn.execute(
                    """
                    UPDATE users
                    SET
                        role = ?,
                        is_active = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        role,
                        1 if is_active else 0,
                        now,
                        user_id,
                    ),
                )
            elif role is not None:
                cursor = conn.execute(
                    """
                    UPDATE users
                    SET
                        role = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        role,
                        now,
                        user_id,
                    ),
                )
            elif is_active is not None:
                cursor = conn.execute(
                    """
                    UPDATE users
                    SET
                        is_active = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        1 if is_active else 0,
                        now,
                        user_id,
                    ),
                )
            else:
                return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        raise

    if cursor.rowcount == 0:
        return None

    return get_user_by_id(user_id)


def update_user_password(
    user_id: int,
    *,
    new_password: str,
    must_change_password: bool,
) -> dict[str, Any] | None:
    init_db()

    validate_password_policy(new_password)

    now = format_datetime(utc_now())
    password_hash = hash_password(new_password)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET
                password_hash = ?,
                password_changed_at = ?,
                must_change_password = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                password_hash,
                now,
                1 if must_change_password else 0,
                now,
                user_id,
            ),
        )

    if cursor.rowcount == 0:
        return None

    return get_user_by_id(user_id)


def record_successful_login(user_id: int) -> None:
    init_db()

    now = format_datetime(utc_now())

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE users
            SET
                failed_login_count = 0,
                last_login_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, user_id),
        )


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    user = get_user_by_username(username)

    if user is None:
        return None

    if not user["is_active"]:
        return None

    if not verify_password(user["password_hash"], password):
        return None

    record_successful_login(user["id"])

    refreshed_user = get_user_by_id(user["id"])
    if refreshed_user is None:
        return None

    return refreshed_user


def get_user_for_session_token(token: str) -> dict[str, Any] | None:
    session = get_active_session_by_token(token)

    if session is None:
        return None

    user = get_user_by_id(session["user_id"])

    if user is None or not user["is_active"]:
        return None

    touch_session(token)

    return user
