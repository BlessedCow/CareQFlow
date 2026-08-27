from __future__ import annotations

from typing import Any


def add_core_authorization_columns(conn: Any) -> None:
    auth_columns = {
        str(row["name"]) for row in conn.execute("PRAGMA table_info(auths)").fetchall()
    }

    auth_column_definitions = (
        ("member_id", "TEXT"),
        ("auth_number", "TEXT"),
        ("group_number", "TEXT"),
        ("date_of_birth", "TEXT"),
        ("insurance", "TEXT"),
        ("insurance_fax", "TEXT"),
        ("requested_days", "INTEGER NOT NULL DEFAULT 0"),
        ("approved_days", "INTEGER NOT NULL DEFAULT 0"),
        ("review_due_date", "TEXT"),
        ("programming_days", "TEXT"),
        ("submitted_at", "TEXT"),
        ("decision_at", "TEXT"),
    )

    for column_name, definition in auth_column_definitions:
        if column_name not in auth_columns:
            conn.execute(f"ALTER TABLE auths ADD COLUMN {column_name} {definition}")

    event_columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(auth_events)").fetchall()
    }

    event_column_definitions = (
        ("requested_days", "INTEGER NOT NULL DEFAULT 0"),
        ("approved_days", "INTEGER NOT NULL DEFAULT 0"),
        ("auth_start_date", "TEXT"),
        ("auth_end_date", "TEXT"),
        ("review_due_date", "TEXT"),
    )

    for column_name, definition in event_column_definitions:
        if column_name not in event_columns:
            conn.execute(
                f"ALTER TABLE auth_events ADD COLUMN {column_name} {definition}"
            )


def add_denial_follow_up_columns(conn: Any) -> None:
    auth_columns = {
        str(row["name"]) for row in conn.execute("PRAGMA table_info(auths)").fetchall()
    }

    column_definitions = (
        ("denial_reason_category", "TEXT"),
        ("denial_reason_notes", "TEXT"),
        ("denial_prevention_notes", "TEXT"),
        ("denied_days", "INTEGER NOT NULL DEFAULT 0"),
        ("denial_date", "TEXT"),
        ("denial_through_date", "TEXT"),
        ("denial_level_of_care", "TEXT"),
        ("denial_source", "TEXT"),
        ("p2p_requested", "INTEGER NOT NULL DEFAULT 0"),
        ("p2p_scheduled_at", "TEXT"),
        ("p2p_deadline", "TEXT"),
        ("p2p_outcome", "TEXT"),
        ("p2p_reviewer", "TEXT"),
        ("p2p_notes", "TEXT"),
        ("appeal_submitted", "INTEGER NOT NULL DEFAULT 0"),
        ("appeal_deadline", "TEXT"),
        ("appeal_outcome", "TEXT"),
        ("appeal_notes", "TEXT"),
        ("retro_requested", "INTEGER NOT NULL DEFAULT 0"),
        ("retro_deadline", "TEXT"),
        ("retro_outcome", "TEXT"),
        ("retro_notes", "TEXT"),
    )

    for column_name, definition in column_definitions:
        if column_name not in auth_columns:
            conn.execute(f"ALTER TABLE auths ADD COLUMN {column_name} {definition}")
