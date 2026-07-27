from __future__ import annotations

import json

import pytest

from authstatus_api.audit.service import (
    audit_field_names,
    list_audit_events,
    record_audit_event,
)
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", generate_encryption_key())
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(tmp_path / "auth_tracker.db"))
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_init_db_creates_audit_events_table():
    init_db()

    with get_conn() as conn:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(audit_events)").fetchall()
        }

    assert {
        "id",
        "user_id",
        "username",
        "action",
        "resource_type",
        "resource_id",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
    }.issubset(columns)


def test_record_audit_event_stores_user_and_metadata():
    user = create_user(
        "audit@example.com", "correct horse battery staple", role="Admin"
    )

    event = record_audit_event(
        action="auth.update",
        resource_type="auth",
        resource_id=123,
        user=user,
        metadata={"fields": ["status"]},
    )

    assert event["user_id"] == user["id"]
    assert event["username"] == "audit@example.com"
    assert event["action"] == "auth.update"
    assert event["resource_type"] == "auth"
    assert event["resource_id"] == 123
    assert json.loads(event["metadata"]) == {"fields": ["status"]}
    assert event["created_at"]


def test_audit_field_names_logs_only_field_names():
    metadata = audit_field_names(
        {
            "client_name": "Sensitive Name",
            "member_id": "ABC123",
            "status": "Approved",
        }
    )

    assert metadata == {"fields": ["client_name", "member_id", "status"]}


def test_list_audit_events_returns_newest_first_with_pagination():
    user = create_user(
        "audit@example.com", "correct horse battery staple", role="Admin"
    )

    for resource_id in range(1, 4):
        record_audit_event(
            action="auth.update",
            resource_type="auth",
            resource_id=resource_id,
            user=user,
        )

    result = list_audit_events(page=1, page_size=2)

    assert result["total"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 2
    assert [event["resource_id"] for event in result["events"]] == [3, 2]


def test_list_audit_events_filters_by_partial_action_and_username():
    admin = create_user(
        "admin@example.com",
        "correct horse battery staple",
        role="Admin",
    )
    read_only_user = create_user(
        "readonly@example.com",
        "correct horse battery staple",
        role="Read Only",
    )

    record_audit_event(
        action="auth.update",
        resource_type="auth",
        user=admin,
    )
    record_audit_event(
        action="security.login",
        resource_type="session",
        user=read_only_user,
    )

    result = list_audit_events(
        action="login",
        username="read",
    )

    assert result["total"] == 1
    assert result["events"][0]["action"] == "security.login"
    assert result["events"][0]["username"] == "readonly@example.com"


def test_list_audit_events_treats_sql_wildcards_as_literal_text():
    user = create_user(
        "audit_user@example.com",
        "correct horse battery staple",
        role="Admin",
    )

    record_audit_event(
        action="auth.update",
        resource_type="auth",
        user=user,
    )

    action_result = list_audit_events(action="%")
    username_result = list_audit_events(username="_")

    assert action_result["total"] == 0
    assert username_result["total"] == 1
    assert username_result["events"][0]["username"] == "audit_user@example.com"
