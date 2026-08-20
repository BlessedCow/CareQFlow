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
            previous_hash TEXT,
            event_hash TEXT,
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
    ensure_column(conn, "audit_events", "previous_hash", "TEXT")
    ensure_column(conn, "audit_events", "event_hash", "TEXT")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS audit_chain_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        head_event_id INTEGER,
        head_event_hash TEXT,
        state_hash TEXT
    )
    """)
