from __future__ import annotations

from typing import Any

from authstatus_api.persistence.migrations import ensure_column


def initialize_authorization_tables(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility TEXT NOT NULL,
            client_name TEXT NOT NULL,
            member_id TEXT,
            auth_number TEXT,
            group_number TEXT,
            date_of_birth TEXT,
            loc TEXT NOT NULL,
            insurance TEXT,
            insurance_phone TEXT,
            insurance_fax TEXT,
            submission_methods TEXT NOT NULL,
            portal_name TEXT,
            fax_numbers TEXT,
            live_call_type TEXT,
            scheduled_call_at TEXT,
            care_manager_enabled INTEGER NOT NULL DEFAULT 0,
            care_manager_details TEXT,
            notes_links TEXT,
            auth_type TEXT NOT NULL,
            status TEXT NOT NULL,
            discharge_clinical_needed INTEGER NOT NULL DEFAULT 0,
            no_pa_required INTEGER NOT NULL DEFAULT 0,
            progress_made INTEGER NOT NULL DEFAULT 0,
            facility_informed INTEGER NOT NULL DEFAULT 0,
            waiting_on_clinicals INTEGER NOT NULL DEFAULT 0,
            los_requested TEXT,
            days_approved TEXT,
            requested_days INTEGER NOT NULL DEFAULT 0,
            approved_days INTEGER NOT NULL DEFAULT 0,
            auth_start_date TEXT,
            auth_end_date TEXT,
            programming_days TEXT,
            submitted_at TEXT,
            review_due_date TEXT,
            decision_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS auth_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT,
            outcome TEXT,
            notes TEXT,
            requested_days INTEGER NOT NULL DEFAULT 0,
            approved_days INTEGER NOT NULL DEFAULT 0,
            auth_start_date TEXT,
            auth_end_date TEXT,
            review_due_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (auth_id) REFERENCES auths (id) ON DELETE CASCADE
        )
        """)

    ensure_column(conn, "auths", "member_id", "TEXT")
    ensure_column(conn, "auths", "auth_number", "TEXT")
    ensure_column(conn, "auths", "group_number", "TEXT")
    ensure_column(conn, "auths", "date_of_birth", "TEXT")
    ensure_column(conn, "auths", "insurance", "TEXT")
    ensure_column(conn, "auths", "insurance_fax", "TEXT")
    ensure_column(
        conn,
        "auths",
        "requested_days",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "auths",
        "approved_days",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(conn, "auths", "review_due_date", "TEXT")
    ensure_column(conn, "auths", "programming_days", "TEXT")
    ensure_column(conn, "auths", "submitted_at", "TEXT")
    ensure_column(conn, "auths", "decision_at", "TEXT")

    ensure_column(
        conn,
        "auth_events",
        "requested_days",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(
        conn,
        "auth_events",
        "approved_days",
        "INTEGER NOT NULL DEFAULT 0",
    )
    ensure_column(conn, "auth_events", "auth_start_date", "TEXT")
    ensure_column(conn, "auth_events", "auth_end_date", "TEXT")
    ensure_column(conn, "auth_events", "review_due_date", "TEXT")
