from __future__ import annotations

from typing import Any


def add_governance_document_revision(conn: Any) -> None:
    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(governance_attestations)").fetchall()
    }

    if "document_revision" not in existing_columns:
        conn.execute("""
            ALTER TABLE governance_attestations
            ADD COLUMN document_revision TEXT
            """)
