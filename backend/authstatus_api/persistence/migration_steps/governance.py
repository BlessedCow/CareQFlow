from __future__ import annotations

from typing import Any


def enforce_append_only_governance_attestations(conn: Any) -> None:
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS governance_attestations_prevent_update
        BEFORE UPDATE ON governance_attestations
        BEGIN
            SELECT RAISE(
                ABORT,
                'governance attestations are append-only'
            );
        END
        """)

    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS governance_attestations_prevent_delete
        BEFORE DELETE ON governance_attestations
        BEGIN
            SELECT RAISE(
                ABORT,
                'governance attestations are append-only'
            );
        END
        """)
