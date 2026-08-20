from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.security.users import FAILED_LOGIN_LOCK_THRESHOLD

SECURITY_MONITORING_WINDOW_HOURS = 24

SECURITY_FAILURE_ACTIONS = (
    "security.login_failed",
    "security.login_locked",
    "security.login_mfa_failed",
    "security.login_mfa_challenge_invalid",
)


def _window_start(hours: int) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat(timespec="seconds")


def get_security_monitoring_summary(
    *,
    hours: int = SECURITY_MONITORING_WINDOW_HOURS,
) -> dict[str, Any]:
    init_db()

    since = _window_start(hours)

    with get_conn() as conn:
        failed_logins = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM audit_events
            WHERE action = ?
              AND created_at >= ?
            """,
            (
                "security.login_failed",
                since,
            ),
        ).fetchone()["total"]

        locked_logins = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM audit_events
            WHERE action = ?
              AND created_at >= ?
            """,
            (
                "security.login_locked",
                since,
            ),
        ).fetchone()["total"]

        failed_mfa = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM audit_events
            WHERE action IN (?, ?)
              AND created_at >= ?
            """,
            (
                "security.login_mfa_failed",
                "security.login_mfa_challenge_invalid",
                since,
            ),
        ).fetchone()["total"]

        distinct_failure_ips = conn.execute(
            """
            SELECT COUNT(DISTINCT ip_address) AS total
            FROM audit_events
            WHERE action IN (?, ?, ?, ?)
              AND created_at >= ?
              AND ip_address != ''
            """,
            (
                *SECURITY_FAILURE_ACTIONS,
                since,
            ),
        ).fetchone()["total"]

        distinct_failure_usernames = conn.execute(
            """
            SELECT COUNT(DISTINCT username) AS total
            FROM audit_events
            WHERE action IN (?, ?, ?, ?)
              AND created_at >= ?
              AND username IS NOT NULL
              AND username != ''
            """,
            (
                *SECURITY_FAILURE_ACTIONS,
                since,
            ),
        ).fetchone()["total"]

        max_failures_single_username_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM audit_events
            WHERE action IN (?, ?, ?, ?)
              AND created_at >= ?
              AND username IS NOT NULL
              AND username != ''
            GROUP BY username
            ORDER BY total DESC
            LIMIT 1
            """,
            (
                *SECURITY_FAILURE_ACTIONS,
                since,
            ),
        ).fetchone()

        max_failures_single_ip_row = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM audit_events
            WHERE action IN (?, ?, ?, ?)
              AND created_at >= ?
              AND ip_address != ''
            GROUP BY ip_address
            ORDER BY total DESC
            LIMIT 1
            """,
            (
                *SECURITY_FAILURE_ACTIONS,
                since,
            ),
        ).fetchone()

    max_failures_single_username = (
        max_failures_single_username_row["total"]
        if max_failures_single_username_row is not None
        else 0
    )
    max_failures_single_ip = (
        max_failures_single_ip_row["total"]
        if max_failures_single_ip_row is not None
        else 0
    )

    total_failures = failed_logins + locked_logins + failed_mfa

    if locked_logins > 0 or max_failures_single_username >= FAILED_LOGIN_LOCK_THRESHOLD:
        severity = "high"
    elif failed_mfa >= FAILED_LOGIN_LOCK_THRESHOLD:
        severity = "elevated"
    else:
        severity = "normal"

    return {
        "window_hours": hours,
        "failed_logins": failed_logins,
        "locked_logins": locked_logins,
        "failed_mfa": failed_mfa,
        "total_failures": total_failures,
        "distinct_failure_ips": distinct_failure_ips,
        "distinct_failure_usernames": distinct_failure_usernames,
        "max_failures_single_username": max_failures_single_username,
        "max_failures_single_ip": max_failures_single_ip,
        "severity": severity,
    }
