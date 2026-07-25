from __future__ import annotations

from typing import Any

from authstatus_api.persistence.migrations import ensure_column


def initialize_audit_tables(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id INTEGER,
            metadata TEXT NOT NULL DEFAULT '{}',
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
        """)

    ensure_column(conn, "audit_events", "user_id", "INTEGER")
    ensure_column(conn, "audit_events", "username", "TEXT")
    ensure_column(
        conn,
        "audit_events",
        "metadata",
        "TEXT NOT NULL DEFAULT '{}'",
    )
    ensure_column(conn, "audit_events", "ip_address", "TEXT")
    ensure_column(conn, "audit_events", "user_agent", "TEXT")
