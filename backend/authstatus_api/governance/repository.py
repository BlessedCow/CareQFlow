from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db

CURRENT_GOVERNANCE_ATTESTATION_VERSION = 1

SUPPORTED_DEPLOYMENT_MODES = {
    "self_hosted",
    "managed",
}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row_to_attestation(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None

    return dict(row)


def get_latest_governance_attestation() -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                governance_attestations.*,
                users.username AS accepted_by_username
            FROM governance_attestations
            JOIN users
                ON users.id = governance_attestations.accepted_by_user_id
            ORDER BY id DESC
            LIMIT 1
            """).fetchone()

    return _row_to_attestation(row)


def get_governance_attestation_history() -> list[dict[str, Any]]:
    init_db()

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                governance_attestations.*,
                users.username AS accepted_by_username
            FROM governance_attestations
            JOIN users
                ON users.id = governance_attestations.accepted_by_user_id
            ORDER BY governance_attestations.id DESC
            """).fetchall()

    return [dict(row) for row in rows]


def get_current_governance_attestation() -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                governance_attestations.*,
                users.username AS accepted_by_username
            FROM governance_attestations
            JOIN users
                ON users.id = governance_attestations.accepted_by_user_id
            WHERE governance_attestations.attestation_version = ?
            ORDER BY governance_attestations.id DESC
            LIMIT 1
            """,
            (CURRENT_GOVERNANCE_ATTESTATION_VERSION,),
        ).fetchone()

    return _row_to_attestation(row)


def is_governance_attestation_current() -> bool:
    return get_current_governance_attestation() is not None


def create_governance_attestation(
    *,
    organization_name: str,
    deployment_mode: str,
    accepted_by_user_id: int,
    app_version: str,
) -> dict[str, Any]:
    init_db()

    normalized_organization_name = " ".join(organization_name.split())

    if not normalized_organization_name:
        raise ValueError("Organization name is required.")

    if deployment_mode not in SUPPORTED_DEPLOYMENT_MODES:
        raise ValueError("Invalid deployment mode.")

    accepted_at = _now()

    with get_conn() as conn:
        cursor = conn.execute(
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
                CURRENT_GOVERNANCE_ATTESTATION_VERSION,
                normalized_organization_name,
                deployment_mode,
                accepted_by_user_id,
                accepted_at,
                app_version,
            ),
        )

        attestation_id = int(cursor.lastrowid)

        row = conn.execute(
            """
            SELECT
                governance_attestations.*,
                users.username AS accepted_by_username
            FROM governance_attestations
            JOIN users
                ON users.id = governance_attestations.accepted_by_user_id
            WHERE governance_attestations.id = ?
            """,
            (attestation_id,),
        ).fetchone()

    attestation = _row_to_attestation(row)

    if attestation is None:
        raise RuntimeError("Unable to retrieve governance attestation.")

    return attestation
