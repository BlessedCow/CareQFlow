from __future__ import annotations

from typing import Any


def initialize_governance_tables(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS governance_attestations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attestation_version INTEGER NOT NULL,
            organization_name TEXT NOT NULL,
            deployment_mode TEXT NOT NULL,
            accepted_by_user_id INTEGER NOT NULL,
            accepted_at TEXT NOT NULL,
            app_version TEXT NOT NULL,
            document_revision TEXT,
            FOREIGN KEY (accepted_by_user_id)
                REFERENCES users (id)
                ON DELETE RESTRICT,
            CHECK (attestation_version >= 1),
            CHECK (
                deployment_mode IN (
                    'self_hosted',
                    'managed'
                )
            )
        )
        """)
