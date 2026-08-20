from __future__ import annotations

import hmac
from typing import Any

from authstatus_api.audit.chain import (
    AUDIT_CHAIN_GENESIS,
    hash_audit_chain_state,
    hash_audit_event,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db


def verify_audit_chain() -> dict[str, Any]:
    init_db()

    with get_conn() as conn:
        legacy_event_count = conn.execute("""
            SELECT COUNT(*) AS total
            FROM audit_events
            WHERE event_hash IS NULL
            """).fetchone()["total"]

        rows = conn.execute("""
            SELECT
                id,
                user_id,
                username,
                action,
                resource_type,
                resource_id,
                metadata,
                ip_address,
                user_agent,
                created_at,
                previous_hash,
                event_hash
            FROM audit_events
            WHERE event_hash IS NOT NULL
            ORDER BY id ASC
            """).fetchall()

        chain_state = conn.execute("""
            SELECT
                head_event_id,
                head_event_hash,
                state_hash
            FROM audit_chain_state
            WHERE id = 1
            """).fetchone()

    if not rows:
        if chain_state is not None:
            return {
                "valid": False,
                "status": "invalid",
                "checked_events": 0,
                "legacy_events": legacy_event_count,
                "failed_event_id": None,
                "reason": "Audit chain state exists without chained audit events.",
            }

        return {
            "valid": True,
            "status": "not_initialized",
            "checked_events": 0,
            "legacy_events": legacy_event_count,
            "failed_event_id": None,
            "reason": None,
        }

    if chain_state is None:
        return {
            "valid": False,
            "status": "invalid",
            "checked_events": 0,
            "legacy_events": legacy_event_count,
            "failed_event_id": None,
            "reason": "Audit chain state is missing.",
        }

    if (
        chain_state["head_event_id"] is None
        or chain_state["head_event_hash"] is None
        or chain_state["state_hash"] is None
    ):
        return {
            "valid": False,
            "status": "invalid",
            "checked_events": 0,
            "legacy_events": legacy_event_count,
            "failed_event_id": None,
            "reason": "Audit chain state is incomplete.",
        }

    expected_state_hash = hash_audit_chain_state(
        head_event_id=chain_state["head_event_id"],
        head_event_hash=chain_state["head_event_hash"],
    )

    if not hmac.compare_digest(
        chain_state["state_hash"],
        expected_state_hash,
    ):
        return {
            "valid": False,
            "status": "invalid",
            "checked_events": 0,
            "legacy_events": legacy_event_count,
            "failed_event_id": None,
            "reason": "Audit chain state integrity check failed.",
        }

    expected_previous_hash = AUDIT_CHAIN_GENESIS
    checked_events = 0

    for row in rows:
        if row["previous_hash"] != expected_previous_hash:
            return {
                "valid": False,
                "status": "invalid",
                "checked_events": checked_events,
                "legacy_events": legacy_event_count,
                "failed_event_id": row["id"],
                "reason": "Audit chain link integrity check failed.",
            }

        expected_event_hash = hash_audit_event(
            event_id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            action=row["action"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            metadata=row["metadata"],
            ip_address=row["ip_address"],
            user_agent=row["user_agent"],
            created_at=row["created_at"],
            previous_hash=row["previous_hash"],
        )

        if not hmac.compare_digest(
            row["event_hash"],
            expected_event_hash,
        ):
            return {
                "valid": False,
                "status": "invalid",
                "checked_events": checked_events,
                "legacy_events": legacy_event_count,
                "failed_event_id": row["id"],
                "reason": "Audit event integrity check failed.",
            }

        expected_previous_hash = row["event_hash"]
        checked_events += 1

    head_event = rows[-1]

    if (
        chain_state["head_event_id"] != head_event["id"]
        or chain_state["head_event_hash"] != head_event["event_hash"]
    ):
        return {
            "valid": False,
            "status": "invalid",
            "checked_events": checked_events,
            "legacy_events": legacy_event_count,
            "failed_event_id": head_event["id"],
            "reason": "Audit chain head integrity check failed.",
        }

    return {
        "valid": True,
        "status": "valid",
        "checked_events": checked_events,
        "legacy_events": legacy_event_count,
        "failed_event_id": None,
        "reason": None,
    }
