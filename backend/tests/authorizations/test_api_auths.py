from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import ENCRYPTED_TEXT_PREFIX, generate_encryption_key
from authstatus_api.main import create_app
from authstatus_api.persistence.connections import get_conn
from authstatus_api.routers import auths as auths_router
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", generate_encryption_key())
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(tmp_path / "auth_tracker.db"))
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.fixture
def auth_headers(client):
    create_user(
        "ur@example.com",
        "correct horse battery staple",
        role="UR",
    )

    response = client.post(
        "/api/security/login",
        json={
            "username": "ur@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 200

    assert client.cookies.get("carequeue_session")

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    return {
        "X-CSRF-Token": csrf_token,
    }


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def make_payload() -> dict:
    return {
        "facility": "Facility A",
        "client_name": "John Smith",
        "member_id": "ABC123",
        "group_number": "GRP456",
        "date_of_birth": "1990-01-15",
        "loc": "RTC",
        "insurance": "Test Plan",
        "insurance_phone": "555-123-4567",
        "insurance_fax": "555-987-6543",
        "submission_methods": "Fax",
        "portal_name": "",
        "fax_numbers": "555-111-2222",
        "live_call_type": "",
        "scheduled_call_at": "",
        "care_manager_enabled": True,
        "care_manager_details": "Jane CM 555-000-0000",
        "notes_links": "Internal note",
        "auth_type": "Concurrent",
        "status": "In Progress",
        "discharge_clinical_needed": False,
        "no_pa_required": False,
        "progress_made": True,
        "facility_informed": False,
        "waiting_on_clinicals": True,
        "los_requested": "7",
        "days_approved": "",
        "auth_start_date": "2026-06-25",
        "auth_end_date": "",
    }


def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "AuthStatus API",
        "version": "0.1.0",
    }


def test_create_auth_endpoint_returns_decrypted_record(client, auth_headers):
    response = client.post("/api/auths", json=make_payload(), headers=auth_headers)

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 1
    assert data["client_name"] == "John Smith"
    assert data["member_id"] == "ABC123"
    assert data["group_number"] == "GRP456"
    assert data["date_of_birth"] == "1990-01-15"
    assert data["facility"] == "Facility A"
    assert data["care_manager_enabled"] is True
    assert data["progress_made"] is True
    assert data["waiting_on_clinicals"] is True


def test_create_auth_endpoint_stores_selected_fields_encrypted(client, auth_headers):
    response = client.post("/api/auths", json=make_payload(), headers=auth_headers)

    assert response.status_code == 201

    database_path = get_settings().database_path

    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM auths WHERE id = 1").fetchone()

    assert row is not None
    assert row["client_name"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert row["member_id"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert row["group_number"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert row["date_of_birth"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert row["insurance_phone"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert row["insurance_fax"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert row["fax_numbers"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert row["facility"] == "Facility A"
    assert row["loc"] == "RTC"


def test_list_auths_endpoint_returns_decrypted_records(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    response = client.get("/api/auths", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    assert len(data["auths"]) == 1
    assert data["auths"][0]["client_name"] == "John Smith"
    assert data["auths"][0]["member_id"] == "ABC123"
    assert data["auths"][0]["group_number"] == "GRP456"
    assert data["auths"][0]["date_of_birth"] == "1990-01-15"


def test_get_auth_endpoint_returns_decrypted_record(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    response = client.get("/api/auths/1", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["client_name"] == "John Smith"
    assert data["member_id"] == "ABC123"


def test_get_auth_endpoint_returns_404_for_missing_record(client, auth_headers):
    response = client.get("/api/auths/999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Auth record not found."}


def test_delete_auth_endpoint_removes_record(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    delete_response = client.delete("/api/auths/1", headers=auth_headers)

    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True, "id": 1}

    get_response = client.get("/api/auths/1", headers=auth_headers)

    assert get_response.status_code == 404


def test_delete_auth_endpoint_returns_404_for_missing_record(client, auth_headers):
    response = client.delete("/api/auths/999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Auth record not found."}


def test_create_auth_endpoint_rejects_unknown_fields(client, auth_headers):
    payload = make_payload()
    payload["unexpected_field"] = "not allowed"

    response = client.post("/api/auths", json=payload, headers=auth_headers)

    assert response.status_code == 422


def test_validation_error_response_does_not_echo_request_payload(
    client,
    auth_headers,
):
    payload = make_payload()
    payload["unexpected_field"] = "John Smith ABC123 should not be echoed"

    response = client.post("/api/auths", json=payload, headers=auth_headers)

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid request."}
    assert "John Smith" not in response.text
    assert "ABC123" not in response.text


def test_internal_error_response_does_not_expose_exception_message(
    monkeypatch,
):
    def fail_list_auths() -> list[dict]:
        raise RuntimeError("John Smith ABC123 internal failure")

    monkeypatch.setattr(auths_router, "list_auths", fail_list_auths)

    with TestClient(create_app(), raise_server_exceptions=False) as safe_client:
        create_user(
            "ur@example.com",
            "correct horse battery staple",
            role="UR",
        )

        login_response = safe_client.post(
            "/api/security/login",
            json={
                "username": "ur@example.com",
                "password": "correct horse battery staple",
            },
        )

        assert login_response.status_code == 200

        response = safe_client.get("/api/auths")

    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected error occurred."}
    assert "John Smith" not in response.text
    assert "ABC123" not in response.text
    assert "internal failure" not in response.text


def test_patch_auth_endpoint_updates_selected_fields(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    response = client.patch(
        "/api/auths/1",
        json={
            "status": "Submitted",
            "days_approved": "4",
            "facility_informed": True,
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["status"] == "Submitted"
    assert data["days_approved"] == "4"
    assert data["facility_informed"] is True
    assert data["client_name"] == "John Smith"


def test_patch_auth_endpoint_encrypts_updated_sensitive_fields(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    response = client.patch(
        "/api/auths/1",
        json={
            "client_name": "Jane Smith",
            "member_id": "XYZ789",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["client_name"] == "Jane Smith"
    assert data["member_id"] == "XYZ789"

    database_path = get_settings().database_path

    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM auths WHERE id = 1").fetchone()

    assert row is not None
    assert row["client_name"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert row["member_id"].startswith(ENCRYPTED_TEXT_PREFIX)
    assert "Jane Smith" not in row["client_name"]
    assert "XYZ789" not in row["member_id"]


def test_patch_auth_endpoint_returns_404_for_missing_record(client, auth_headers):
    response = client.patch(
        "/api/auths/999",
        json={"status": "Submitted"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Auth record not found."}


def test_patch_auth_endpoint_rejects_unknown_fields(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    response = client.patch(
        "/api/auths/1",
        json={"unexpected_field": "not allowed"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def audit_rows() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT action, resource_type, resource_id, username, metadata
            FROM audit_events
            ORDER BY id
            """).fetchall()

    return [dict(row) for row in rows]


def test_create_auth_writes_audit_event(client, auth_headers):
    response = client.post("/api/auths", json=make_payload(), headers=auth_headers)

    assert response.status_code == 201

    created = response.json()
    rows = audit_rows()

    assert rows[-1]["action"] == "auth.create"
    assert rows[-1]["resource_type"] == "auth"
    assert rows[-1]["resource_id"] == created["id"]
    assert rows[-1]["username"] == "ur@example.com"

    metadata = json.loads(rows[-1]["metadata"])

    assert "fields" in metadata
    assert "client_name" in metadata["fields"]
    assert "member_id" in metadata["fields"]
    assert "John Smith" not in rows[-1]["metadata"]
    assert "ABC123" not in rows[-1]["metadata"]


def test_update_auth_writes_audit_event_without_phi_values(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    response = client.patch(
        "/api/auths/1",
        json={
            "client_name": "Jane Smith",
            "member_id": "XYZ789",
            "status": "Submitted",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    rows = audit_rows()

    assert rows[-1]["action"] == "auth.update"
    assert rows[-1]["resource_type"] == "auth"
    assert rows[-1]["resource_id"] == 1
    assert rows[-1]["username"] == "ur@example.com"

    metadata = json.loads(rows[-1]["metadata"])

    assert metadata == {"fields": ["client_name", "member_id", "status"]}
    assert "Jane Smith" not in rows[-1]["metadata"]
    assert "XYZ789" not in rows[-1]["metadata"]


def test_delete_auth_writes_audit_event(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    response = client.delete("/api/auths/1", headers=auth_headers)

    assert response.status_code == 200

    rows = audit_rows()

    assert rows[-1]["action"] == "auth.delete"
    assert rows[-1]["resource_type"] == "auth"
    assert rows[-1]["resource_id"] == 1
    assert rows[-1]["username"] == "ur@example.com"


def test_auth_routes_require_authentication(client):
    response = client.get("/api/auths")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_read_only_user_can_view_auths(client):
    create_user(
        "readonly@example.com", "correct horse battery staple", role="Read Only"
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "readonly@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    token = client.cookies.get("carequeue_session")

    assert token

    response = client.get(
        "/api/auths",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_read_only_user_cannot_create_auth(client):
    create_user(
        "readonly@example.com", "correct horse battery staple", role="Read Only"
    )

    login_response = client.post(
        "/api/security/login",
        json={
            "username": "readonly@example.com",
            "password": "correct horse battery staple",
        },
    )

    assert login_response.status_code == 200

    assert client.cookies.get("carequeue_session")

    csrf_token = client.cookies.get("carequeue_csrf")

    assert csrf_token

    response = client.post(
        "/api/auths",
        json=make_payload(),
        headers={
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Operation not permitted for this role."}


def make_event_payload() -> dict:
    return {
        "event_type": "Initial Review",
        "event_date": "2026-01-02",
        "event_time": "",
        "outcome": "Approved",
        "auth_start_date": "2026-01-02",
        "auth_end_date": "2026-01-05",
        "review_due_date": "2026-01-06",
        "requested_days": 4,
        "approved_days": 4,
        "notes": "Do not store this note in audit metadata.",
    }


def test_create_auth_event_writes_audit_event_without_note_value(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    response = client.post(
        "/api/auths/1/events",
        json=make_event_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 201

    event = response.json()
    rows = audit_rows()

    assert rows[-1]["action"] == "auth_event.create"
    assert rows[-1]["resource_type"] == "auth_event"
    assert rows[-1]["resource_id"] == event["id"]
    assert rows[-1]["username"] == "ur@example.com"

    metadata = json.loads(rows[-1]["metadata"])

    assert metadata["auth_id"] == 1
    assert "fields" in metadata
    assert "notes" in metadata["fields"]
    assert "Do not store this note" not in rows[-1]["metadata"]


def test_update_auth_event_writes_audit_event_without_note_value(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    event_response = client.post(
        "/api/auths/1/events",
        json=make_event_payload(),
        headers=auth_headers,
    )

    assert event_response.status_code == 201

    response = client.patch(
        "/api/auths/1/events/1",
        json={
            "outcome": "Denied",
            "notes": "Sensitive update note should not be in audit metadata.",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200

    rows = audit_rows()

    assert rows[-1]["action"] == "auth_event.update"
    assert rows[-1]["resource_type"] == "auth_event"
    assert rows[-1]["resource_id"] == 1
    assert rows[-1]["username"] == "ur@example.com"

    metadata = json.loads(rows[-1]["metadata"])

    assert metadata == {"auth_id": 1, "fields": ["notes", "outcome"]}
    assert "Sensitive update note" not in rows[-1]["metadata"]


def test_delete_auth_event_writes_audit_event(client, auth_headers):
    create_response = client.post(
        "/api/auths", json=make_payload(), headers=auth_headers
    )

    assert create_response.status_code == 201

    event_response = client.post(
        "/api/auths/1/events",
        json=make_event_payload(),
        headers=auth_headers,
    )

    assert event_response.status_code == 201

    response = client.delete("/api/auths/1/events/1", headers=auth_headers)

    assert response.status_code == 200

    rows = audit_rows()

    assert rows[-1]["action"] == "auth_event.delete"
    assert rows[-1]["resource_type"] == "auth_event"
    assert rows[-1]["resource_id"] == 1
    assert rows[-1]["username"] == "ur@example.com"
    assert json.loads(rows[-1]["metadata"]) == {"auth_id": 1}


def test_analytics_summary_endpoint_counts_records(client, auth_headers):
    first_payload = make_payload()
    second_payload = make_payload()
    second_payload["client_name"] = "Jane Smith"
    second_payload["member_id"] = "XYZ789"
    second_payload["loc"] = "PHP"
    second_payload["auth_type"] = "Initial"
    second_payload["status"] = "Submitted"
    second_payload["no_pa_required"] = True
    second_payload["waiting_on_clinicals"] = False

    assert (
        client.post("/api/auths", json=first_payload, headers=auth_headers).status_code
        == 201
    )
    assert (
        client.post("/api/auths", json=second_payload, headers=auth_headers).status_code
        == 201
    )

    response = client.get("/api/analytics/summary", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {
        "total_auths": 2,
        "by_status": {
            "Pending": 2,
        },
        "by_loc": {
            "RTC": 1,
            "PHP": 1,
        },
        "by_auth_type": {
            "Concurrent": 1,
            "Initial": 1,
        },
        "no_pa_required": 1,
        "waiting_on_clinicals": 1,
    }
