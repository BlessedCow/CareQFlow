from __future__ import annotations

import sqlite3

import pytest

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(tmp_path / "auth_tracker.db"))
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def table_columns(table_name: str) -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()

    return {row["name"] for row in rows}


def test_init_db_creates_users_table():
    init_db()

    assert {
        "id",
        "username",
        "password_hash",
        "role",
        "is_active",
        "failed_login_count",
        "locked_until",
        "last_login_at",
        "password_changed_at",
        "must_change_password",
        "created_at",
        "updated_at",
    }.issubset(table_columns("users"))


def test_new_users_do_not_require_password_change_by_default():
    init_db()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                password_changed_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "default-password-state@example.com",
                "test-password-hash",
                "UR",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        row = conn.execute(
            """
            SELECT must_change_password
            FROM users
            WHERE username = ?
            """,
            ("default-password-state@example.com",),
        ).fetchone()

    assert row is not None
    assert row["must_change_password"] == 0


def test_init_db_creates_sessions_table():
    init_db()

    assert {
        "id",
        "user_id",
        "token_hash",
        "created_at",
        "last_seen_at",
        "expires_at",
        "revoked_at",
        "ip_address",
        "user_agent",
    }.issubset(table_columns("sessions"))


def test_user_role_constraint_rejects_unknown_role():
    init_db()

    with pytest.raises(sqlite3.IntegrityError):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    role,
                    password_changed_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "bad-role-user",
                    "$argon2id$placeholder",
                    "Manager",
                    "2026-01-01T00:00:00",
                    "2026-01-01T00:00:00",
                    "2026-01-01T00:00:00",
                ),
            )


def test_deleting_user_removes_sessions():
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                password_changed_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "session-user",
                "$argon2id$placeholder",
                "UR",
                "2026-01-01T00:00:00",
                "2026-01-01T00:00:00",
                "2026-01-01T00:00:00",
            ),
        )
        user_id = cursor.lastrowid

        conn.execute(
            """
            INSERT INTO sessions (
                user_id,
                token_hash,
                created_at,
                last_seen_at,
                expires_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                "hashed-token",
                "2026-01-01T00:00:00",
                "2026-01-01T00:00:00",
                "2026-01-01T00:30:00",
            ),
        )

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

        session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    assert session_count == 0
