from __future__ import annotations

import pytest

from authstatus_api.audit.service import record_audit_event
from authstatus_api.audit.verification import verify_audit_chain
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_audit_verification_test_settings(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def create_audit_chain():
    first_event = record_audit_event(
        action="security.login",
        resource_type="session",
    )
    second_event = record_audit_event(
        action="auth.update",
        resource_type="auth",
        resource_id=101,
    )
    third_event = record_audit_event(
        action="security.logout",
        resource_type="session",
    )

    return first_event, second_event, third_event


def test_verify_audit_chain_reports_not_initialized():
    result = verify_audit_chain()

    assert result == {
        "valid": True,
        "status": "not_initialized",
        "checked_events": 0,
        "legacy_events": 0,
        "failed_event_id": None,
        "reason": None,
    }


def test_verify_audit_chain_accepts_valid_chain():
    create_audit_chain()

    result = verify_audit_chain()

    assert result["valid"] is True
    assert result["status"] == "valid"
    assert result["checked_events"] == 3
    assert result["legacy_events"] == 0
    assert result["failed_event_id"] is None
    assert result["reason"] is None


def test_verify_audit_chain_counts_legacy_events_separately():
    init_db()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (
                action,
                resource_type,
                metadata,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "legacy.event",
                "legacy",
                "{}",
                "2026-01-01T00:00:00+00:00",
            ),
        )

    record_audit_event(
        action="security.login",
        resource_type="session",
    )

    result = verify_audit_chain()

    assert result["valid"] is True
    assert result["status"] == "valid"
    assert result["checked_events"] == 1
    assert result["legacy_events"] == 1


def test_verify_audit_chain_detects_modified_event():
    _, second_event, _ = create_audit_chain()

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE audit_events
            SET action = ?
            WHERE id = ?
            """,
            (
                "tampered.action",
                second_event["id"],
            ),
        )

    result = verify_audit_chain()

    assert result["valid"] is False
    assert result["failed_event_id"] == second_event["id"]
    assert result["reason"] == "Audit event integrity check failed."


def test_verify_audit_chain_detects_deleted_middle_event():
    _, second_event, third_event = create_audit_chain()

    with get_conn() as conn:
        conn.execute(
            "DELETE FROM audit_events WHERE id = ?",
            (second_event["id"],),
        )

    result = verify_audit_chain()

    assert result["valid"] is False
    assert result["failed_event_id"] == third_event["id"]
    assert result["reason"] == "Audit chain link integrity check failed."


def test_verify_audit_chain_detects_deleted_head_event():
    _, _, third_event = create_audit_chain()

    with get_conn() as conn:
        conn.execute(
            "DELETE FROM audit_events WHERE id = ?",
            (third_event["id"],),
        )

    result = verify_audit_chain()

    assert result["valid"] is False
    assert result["reason"] == "Audit chain head integrity check failed."


def test_verify_audit_chain_detects_modified_chain_state():
    create_audit_chain()

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE audit_chain_state
            SET head_event_hash = ?
            WHERE id = 1
            """,
            ("0" * 64,),
        )

    result = verify_audit_chain()

    assert result["valid"] is False
    assert result["reason"] == "Audit chain state integrity check failed."


def test_verify_audit_chain_detects_missing_chain_state():
    create_audit_chain()

    with get_conn() as conn:
        conn.execute("DELETE FROM audit_chain_state WHERE id = 1")

    result = verify_audit_chain()

    assert result["valid"] is False
    assert result["reason"] == "Audit chain state is missing."
