from __future__ import annotations

import sqlite3

import pytest

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.security.users import create_user
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


def test_init_db_creates_governance_attestations_table():
    init_db()

    assert {
        "id",
        "attestation_version",
        "organization_name",
        "deployment_mode",
        "accepted_by_user_id",
        "accepted_at",
        "app_version",
    }.issubset(table_columns("governance_attestations"))


@pytest.mark.parametrize(
    "deployment_mode",
    [
        "self_hosted",
        "managed",
    ],
)
def test_governance_attestation_accepts_supported_deployment_modes(
    deployment_mode,
):
    init_db()

    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO governance_attestations (
                attestation_version,
                organization_name,
                deployment_mode,
                accepted_by_user_id,
                accepted_at,
                app_version
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "Example Facility",
                deployment_mode,
                admin["id"],
                "2026-08-22T12:00:00+00:00",
                "0.2.0",
            ),
        )


def test_governance_attestation_rejects_unknown_deployment_mode():
    init_db()

    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    with pytest.raises(sqlite3.IntegrityError):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO governance_attestations (
                    attestation_version,
                    organization_name,
                    deployment_mode,
                    accepted_by_user_id,
                    accepted_at,
                    app_version
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    "Example Facility",
                    "unknown",
                    admin["id"],
                    "2026-08-22T12:00:00+00:00",
                    "0.2.0",
                ),
            )


def test_governance_attestation_requires_existing_user():
    init_db()

    with pytest.raises(sqlite3.IntegrityError):
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO governance_attestations (
                    attestation_version,
                    organization_name,
                    deployment_mode,
                    accepted_by_user_id,
                    accepted_at,
                    app_version
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    "Example Facility",
                    "self_hosted",
                    999,
                    "2026-08-22T12:00:00+00:00",
                    "0.2.0",
                ),
            )
