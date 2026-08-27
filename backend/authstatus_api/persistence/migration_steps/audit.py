from __future__ import annotations

from typing import Any


def add_audit_event_columns(conn: Any) -> None:
    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(audit_events)").fetchall()
    }

    columns = (
        ("user_id", "INTEGER"),
        ("username", "TEXT"),
        ("metadata", "TEXT NOT NULL DEFAULT '{}'"),
        ("ip_address", "TEXT"),
        ("user_agent", "TEXT"),
        ("previous_hash", "TEXT"),
        ("event_hash", "TEXT"),
    )

    for column_name, definition in columns:
        if column_name not in existing_columns:
            conn.execute(
                f"ALTER TABLE audit_events " f"ADD COLUMN {column_name} {definition}"
            )
