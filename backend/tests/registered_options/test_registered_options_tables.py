from __future__ import annotations

import sqlite3

import pytest

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def table_columns(table_name: str) -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()

    return {row["name"] for row in rows}


def test_init_db_creates_registered_options_table():
    init_db()

    assert {
        "id",
        "category",
        "name",
        "normalized_name",
        "is_protected",
        "created_at",
        "updated_at",
    }.issubset(table_columns("registered_options"))


def test_init_db_seeds_protected_other_option_for_each_category():
    init_db()

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT category, name, normalized_name, is_protected
            FROM registered_options
            ORDER BY category
            """).fetchall()

    assert [
        (
            row["category"],
            row["name"],
            row["normalized_name"],
            row["is_protected"],
        )
        for row in rows
    ] == [
        ("facility", "Other", "other", 1),
        ("insurance", "Other", "other", 1),
        ("web_portal", "Other", "other", 1),
    ]


def test_init_db_does_not_duplicate_seeded_options():
    init_db()
    init_db()

    with get_conn() as conn:
        count = conn.execute("""
            SELECT COUNT(*)
            FROM registered_options
            """).fetchone()[0]

    assert count == 3


def test_registered_options_reject_unknown_category():
    init_db()

    with pytest.raises(sqlite3.IntegrityError):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO registered_options (
                    category,
                    name,
                    normalized_name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "unknown",
                    "Example",
                    "example",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
            )


def test_registered_options_reject_duplicate_normalized_name_per_category():
    init_db()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO registered_options (
                category,
                name,
                normalized_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "facility",
                "Example Facility",
                "example facility",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

    with pytest.raises(sqlite3.IntegrityError):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO registered_options (
                    category,
                    name,
                    normalized_name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "facility",
                    "EXAMPLE FACILITY",
                    "example facility",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                ),
            )


def test_same_normalized_name_is_allowed_in_different_categories():
    init_db()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO registered_options (
                category,
                name,
                normalized_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "facility",
                "Example",
                "example",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        conn.execute(
            """
            INSERT INTO registered_options (
                category,
                name,
                normalized_name,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "insurance",
                "Example",
                "example",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM registered_options
            WHERE normalized_name = ?
            """,
            ("example",),
        ).fetchone()[0]

    assert count == 2
