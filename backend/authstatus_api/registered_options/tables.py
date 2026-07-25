from __future__ import annotations

from typing import Any

DEFAULT_OPTION_TIMESTAMP = "1970-01-01T00:00:00+00:00"

REGISTERED_OPTION_CATEGORIES = (
    "facility",
    "insurance",
    "web_portal",
)


def initialize_registered_options_table(conn: Any) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS registered_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            is_protected INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (
                category IN (
                    'facility',
                    'insurance',
                    'web_portal'
                )
            ),
            CHECK (is_protected IN (0, 1)),
            UNIQUE (category, normalized_name)
        )
        """)

    for category in REGISTERED_OPTION_CATEGORIES:
        conn.execute(
            """
            INSERT OR IGNORE INTO registered_options (
                category,
                name,
                normalized_name,
                is_protected,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                category,
                "Other",
                "other",
                1,
                DEFAULT_OPTION_TIMESTAMP,
                DEFAULT_OPTION_TIMESTAMP,
            ),
        )
