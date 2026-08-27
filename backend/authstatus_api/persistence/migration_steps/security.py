from __future__ import annotations

from typing import Any


def add_walkthrough_columns(conn: Any) -> None:
    columns = {
        str(row["name"]) for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    if "walkthrough_status" not in columns:
        conn.execute("""
            ALTER TABLE users
            ADD COLUMN walkthrough_status TEXT NOT NULL DEFAULT 'pending'
            CHECK (
                walkthrough_status IN (
                    'pending',
                    'completed',
                    'skipped'
                )
            )
            """)

    if "walkthrough_step" not in columns:
        conn.execute("""
            ALTER TABLE users
            ADD COLUMN walkthrough_step TEXT
            """)


def add_authentication_and_session_columns(conn: Any) -> None:
    user_columns = {
        str(row["name"]) for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    user_column_definitions = (
        ("failed_login_count", "INTEGER NOT NULL DEFAULT 0"),
        ("locked_until", "TEXT"),
        ("last_login_at", "TEXT"),
        ("password_changed_at", "TEXT"),
        ("must_change_password", "INTEGER NOT NULL DEFAULT 0"),
        ("mfa_enabled", "INTEGER NOT NULL DEFAULT 0"),
        ("mfa_secret", "TEXT"),
    )

    for column_name, definition in user_column_definitions:
        if column_name not in user_columns:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column_name} {definition}")

    session_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
    }

    session_column_definitions = (
        ("ip_address", "TEXT"),
        ("user_agent", "TEXT"),
    )

    for column_name, definition in session_column_definitions:
        if column_name not in session_columns:
            conn.execute(f"ALTER TABLE sessions ADD COLUMN {column_name} {definition}")
