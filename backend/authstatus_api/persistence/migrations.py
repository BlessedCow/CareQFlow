from __future__ import annotations

from typing import Any


def ensure_column(
    conn: Any,
    table: str,
    column: str,
    definition: str,
) -> None:
    existing = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }

    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
