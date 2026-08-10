from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from authstatus_api.crypto import ENCRYPTED_TEXT_PREFIX, generate_encryption_key
from authstatus_api.main import create_app
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
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


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

    csrf_token = client.cookies.get("carequeue_csrf")
    assert csrf_token

    return {
        "X-CSRF-Token": csrf_token,
    }


def make_auth_payload() -> dict:
    return {
        "facility": "Facility A",
        "client_name": "John Smith",
        "member_id": "ABC123",
        "auth_number": "UM12345678",
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


def create_auth_record(client, auth_headers) -> dict:
    response = client.post(
        "/api/auths",
        json=make_auth_payload(),
        headers=auth_headers,
    )

    assert response.status_code == 201

    return response.json()


def pdf_headers(auth_headers: dict[str, str]) -> dict[str, str]:
    return {
        **auth_headers,
        "Content-Type": "application/pdf",
    }


def test_upload_auth_document_stores_encrypted_pdf_metadata_only(
    client,
    auth_headers,
):
    auth = create_auth_record(client, auth_headers)
    pdf_bytes = b"%PDF-1.7\napproval letter"

    response = client.post(
        f"/api/auths/{auth['id']}/documents"
        "?document_type=approval_letter&filename=approval.pdf",
        content=pdf_bytes,
        headers=pdf_headers(auth_headers),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["auth_id"] == auth["id"]
    assert data["document_type"] == "approval_letter"
    assert data["original_filename"] == "approval.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["file_size_bytes"] == len(pdf_bytes)
    assert "encrypted_pdf" not in data

    database_path = get_settings().database_path

    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT encrypted_pdf
            FROM auth_documents
            WHERE id = ?
            """,
            (data["id"],),
        ).fetchone()

    assert row is not None
    assert row["encrypted_pdf"].startswith(ENCRYPTED_TEXT_PREFIX.encode())
    assert pdf_bytes not in row["encrypted_pdf"]


def test_list_auth_documents_returns_metadata_only(client, auth_headers):
    auth = create_auth_record(client, auth_headers)

    upload_response = client.post(
        f"/api/auths/{auth['id']}/documents"
        "?document_type=denial_letter&filename=denial.pdf",
        content=b"%PDF-1.7\ndenial letter",
        headers=pdf_headers(auth_headers),
    )

    assert upload_response.status_code == 201

    response = client.get(
        f"/api/auths/{auth['id']}/documents",
        headers=auth_headers,
    )

    assert response.status_code == 200

    documents = response.json()["documents"]

    assert len(documents) == 1
    assert documents[0]["document_type"] == "denial_letter"
    assert documents[0]["original_filename"] == "denial.pdf"
    assert "encrypted_pdf" not in documents[0]


def test_download_auth_document_returns_pdf_with_no_store_headers(
    client,
    auth_headers,
):
    auth = create_auth_record(client, auth_headers)
    pdf_bytes = b"%PDF-1.7\napproval letter"

    upload_response = client.post(
        f"/api/auths/{auth['id']}/documents"
        "?document_type=approval_letter&filename=approval letter.pdf",
        content=pdf_bytes,
        headers=pdf_headers(auth_headers),
    )

    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    response = client.get(
        f"/api/auths/{auth['id']}/documents/{document_id}/pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.content == pdf_bytes
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["cache-control"] == "no-store, private"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["expires"] == "0"
    assert "filename*=UTF-8''approval%20letter.pdf" in (
        response.headers["content-disposition"]
    )


def test_delete_auth_document_removes_document(client, auth_headers):
    auth = create_auth_record(client, auth_headers)

    upload_response = client.post(
        f"/api/auths/{auth['id']}/documents" "?document_type=other&filename=letter.pdf",
        content=b"%PDF-1.7\nother",
        headers=pdf_headers(auth_headers),
    )

    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    delete_response = client.delete(
        f"/api/auths/{auth['id']}/documents/{document_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "deleted": True,
        "id": document_id,
    }

    list_response = client.get(
        f"/api/auths/{auth['id']}/documents",
        headers=auth_headers,
    )

    assert list_response.status_code == 200
    assert list_response.json() == {"documents": []}


def test_upload_auth_document_rejects_non_pdf_content_type(client, auth_headers):
    auth = create_auth_record(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth['id']}/documents"
        "?document_type=approval_letter&filename=approval.txt",
        content=b"not a pdf",
        headers={
            **auth_headers,
            "Content-Type": "text/plain",
        },
    )

    assert response.status_code == 415
    assert response.json() == {"detail": "The request must contain a PDF."}
    assert response.headers["cache-control"] == "no-store, private"


def test_upload_auth_document_rejects_invalid_document_type(client, auth_headers):
    auth = create_auth_record(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth['id']}/documents"
        "?document_type=clinical_notes&filename=notes.pdf",
        content=b"%PDF-1.7\nnotes",
        headers=pdf_headers(auth_headers),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Invalid authorization document type."}
    assert response.headers["cache-control"] == "no-store, private"


def test_upload_auth_document_rejects_non_pdf_bytes(client, auth_headers):
    auth = create_auth_record(client, auth_headers)

    response = client.post(
        f"/api/auths/{auth['id']}/documents"
        "?document_type=approval_letter&filename=approval.pdf",
        content=b"not a pdf",
        headers=pdf_headers(auth_headers),
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "The uploaded document must be a PDF."}
    assert response.headers["cache-control"] == "no-store, private"


def test_auth_document_routes_return_404_for_missing_records(client, auth_headers):
    list_response = client.get("/api/auths/999/documents", headers=auth_headers)

    assert list_response.status_code == 404
    assert list_response.json() == {"detail": "Auth record not found."}

    upload_response = client.post(
        "/api/auths/999/documents?document_type=approval_letter&filename=approval.pdf",
        content=b"%PDF-1.7\napproval",
        headers=pdf_headers(auth_headers),
    )

    assert upload_response.status_code == 404
    assert upload_response.json() == {"detail": "Auth record not found."}

    download_response = client.get(
        "/api/auths/999/documents/1/pdf",
        headers=auth_headers,
    )

    assert download_response.status_code == 404
    assert download_response.json() == {"detail": "Authorization document not found."}

    auth = create_auth_record(client, auth_headers)

    delete_response = client.delete(
        f"/api/auths/{auth['id']}/documents/999",
        headers=auth_headers,
    )

    assert delete_response.status_code == 404
    assert delete_response.json() == {"detail": "Authorization document not found."}


def test_auth_document_audit_events_do_not_include_filename_or_pdf_content(
    client,
    auth_headers,
):
    auth = create_auth_record(client, auth_headers)
    pdf_bytes = b"%PDF-1.7\nsensitive approval letter"

    upload_response = client.post(
        f"/api/auths/{auth['id']}/documents"
        "?document_type=approval_letter&filename=John Smith approval.pdf",
        content=pdf_bytes,
        headers=pdf_headers(auth_headers),
    )

    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]

    download_response = client.get(
        f"/api/auths/{auth['id']}/documents/{document_id}/pdf",
        headers=auth_headers,
    )

    assert download_response.status_code == 200

    delete_response = client.delete(
        f"/api/auths/{auth['id']}/documents/{document_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 200

    database_path = get_settings().database_path

    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT action, metadata
            FROM audit_events
            WHERE action IN (
                'auth_document.create',
                'auth_document.download',
                'auth_document.delete'
            )
            ORDER BY id
            """).fetchall()

    assert [row["action"] for row in rows] == [
        "auth_document.create",
        "auth_document.download",
        "auth_document.delete",
    ]

    for row in rows:
        assert "John Smith" not in row["metadata"]
        assert "approval.pdf" not in row["metadata"]
        assert "sensitive approval letter" not in row["metadata"]

    create_metadata = json.loads(rows[0]["metadata"])

    assert create_metadata == {
        "auth_id": auth["id"],
        "document_type": "approval_letter",
        "file_size_bytes": len(pdf_bytes),
    }


def test_upload_auth_document_returns_safe_storage_limit_error(
    client,
    auth_headers,
    monkeypatch,
):
    monkeypatch.setattr(
        "authstatus_api.authorizations.documents." "MAX_AUTH_DOCUMENT_BYTES_PER_AUTH",
        32,
    )

    auth = create_auth_record(client, auth_headers)

    first_response = client.post(
        f"/api/auths/{auth['id']}/documents" "?document_type=other&filename=first.pdf",
        content=b"%PDF-1.7\nfirst",
        headers=pdf_headers(auth_headers),
    )

    assert first_response.status_code == 201

    response = client.post(
        f"/api/auths/{auth['id']}/documents" "?document_type=other&filename=second.pdf",
        content=b"%PDF-1.7\nsecond file exceeds limit",
        headers=pdf_headers(auth_headers),
    )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Authorization document storage limit exceeded."
    }
    assert response.headers["cache-control"] == "no-store, private"
