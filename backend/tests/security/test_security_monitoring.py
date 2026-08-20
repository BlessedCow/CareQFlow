from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from authstatus_api.audit.service import record_audit_event
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.persistence.connections import get_conn
from authstatus_api.security.monitoring import get_security_monitoring_summary
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_security_monitoring_test_settings(
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


def test_security_monitoring_summary_is_empty_without_failures():
    result = get_security_monitoring_summary()

    assert result == {
        "window_hours": 24,
        "failed_logins": 0,
        "locked_logins": 0,
        "failed_mfa": 0,
        "total_failures": 0,
        "distinct_failure_ips": 0,
        "distinct_failure_usernames": 0,
        "max_failures_single_username": 0,
        "max_failures_single_ip": 0,
        "severity": "normal",
    }


def test_security_monitoring_summary_counts_security_failures():
    record_audit_event(
        action="security.login_failed",
        resource_type="security",
        username="user@example.com",
    )
    record_audit_event(
        action="security.login_locked",
        resource_type="security",
        username="user@example.com",
    )
    record_audit_event(
        action="security.login_mfa_failed",
        resource_type="mfa_login_challenge",
        username="user@example.com",
    )
    record_audit_event(
        action="security.login_mfa_challenge_invalid",
        resource_type="mfa_login_challenge",
    )

    result = get_security_monitoring_summary()

    assert result["failed_logins"] == 1
    assert result["locked_logins"] == 1
    assert result["failed_mfa"] == 2
    assert result["total_failures"] == 4


def test_security_monitoring_summary_counts_distinct_failure_usernames():
    record_audit_event(
        action="security.login_failed",
        resource_type="security",
        username="first@example.com",
    )
    record_audit_event(
        action="security.login_failed",
        resource_type="security",
        username="first@example.com",
    )
    record_audit_event(
        action="security.login_locked",
        resource_type="security",
        username="second@example.com",
    )

    result = get_security_monitoring_summary()

    assert result["distinct_failure_usernames"] == 2


def test_security_monitoring_summary_ignores_successful_security_events():
    record_audit_event(
        action="security.login",
        resource_type="session",
        username="user@example.com",
    )
    record_audit_event(
        action="security.login_mfa_verified",
        resource_type="mfa_login_challenge",
        username="user@example.com",
    )

    result = get_security_monitoring_summary()

    assert result["total_failures"] == 0
    assert result["distinct_failure_usernames"] == 0


def test_security_monitoring_summary_ignores_events_outside_window():
    old_event = record_audit_event(
        action="security.login_failed",
        resource_type="security",
        username="old@example.com",
    )

    old_created_at = (datetime.now(UTC) - timedelta(hours=25)).isoformat(
        timespec="seconds"
    )

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE audit_events
            SET created_at = ?
            WHERE id = ?
            """,
            (
                old_created_at,
                old_event["id"],
            ),
        )

    result = get_security_monitoring_summary()

    assert result["failed_logins"] == 0
    assert result["total_failures"] == 0


def test_security_monitoring_marks_repeated_username_failures_high():
    for _ in range(5):
        record_audit_event(
            action="security.login_failed",
            resource_type="security",
            username="target@example.com",
        )

    result = get_security_monitoring_summary()

    assert result["max_failures_single_username"] == 5
    assert result["severity"] == "high"


def test_security_monitoring_marks_repeated_mfa_failures_elevated():
    for index in range(5):
        record_audit_event(
            action="security.login_mfa_failed",
            resource_type="mfa_login_challenge",
            username=f"user{index}@example.com",
        )

    result = get_security_monitoring_summary()

    assert result["failed_mfa"] == 5
    assert result["max_failures_single_username"] == 1
    assert result["severity"] == "elevated"


def test_security_monitoring_marks_lockout_activity_high():
    record_audit_event(
        action="security.login_locked",
        resource_type="security",
        username="locked@example.com",
    )

    result = get_security_monitoring_summary()

    assert result["locked_logins"] == 1
    assert result["severity"] == "high"
