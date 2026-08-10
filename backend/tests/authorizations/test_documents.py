from __future__ import annotations

import sqlite3

import pytest

from authstatus_api import crypto
from authstatus_api.authorizations.documents import (
    MAX_AUTH_DOCUMENT_BYTES_TOTAL,
    MAX_AUTH_DOCUMENTS_PER_AUTH,
    AuthDocumentLimitError,
    InvalidAuthDocumentError,
    InvalidAuthDocumentTypeError,
    create_auth_document,
    delete_auth_document,
    get_auth_document,
    get_auth_document_pdf,
    list_auth_documents,
)
from authstatus_api.authorizations.records import create_auth, get_auth
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", crypto.generate_encryption_key())
    monkeypatch.setenv("AUTHSTATUS_DATABASE_PATH", str(tmp_path / "auth_tracker.db"))
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


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


def test_create_auth_document_stores_encrypted_pdf_metadata_only():
    auth = create_auth(make_auth_payload())
    pdf_bytes = b"%PDF-1.7\nletter content"

    document = create_auth_document(
        auth["id"],
        document_type="approval_letter",
        original_filename="approval.pdf",
        pdf_bytes=pdf_bytes,
    )

    assert document is not None
    assert document["auth_id"] == auth["id"]
    assert document["document_type"] == "approval_letter"
    assert document["original_filename"] == "approval.pdf"
    assert document["content_type"] == "application/pdf"
    assert document["file_size_bytes"] == len(pdf_bytes)
    assert "encrypted_pdf" not in document

    database_path = get_settings().database_path

    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT encrypted_pdf FROM auth_documents WHERE id = ?",
            (document["id"],),
        ).fetchone()

    assert row is not None
    assert row["encrypted_pdf"].startswith(b"enc:")
    assert pdf_bytes not in row["encrypted_pdf"]


def test_get_auth_document_pdf_returns_decrypted_bytes():
    auth = create_auth(make_auth_payload())
    pdf_bytes = b"%PDF-1.7\napproval letter"
    document = create_auth_document(
        auth["id"],
        document_type="approval_letter",
        original_filename="approval.pdf",
        pdf_bytes=pdf_bytes,
    )

    result = get_auth_document_pdf(auth["id"], document["id"])

    assert result is not None
    metadata, returned_pdf = result
    assert metadata["id"] == document["id"]
    assert returned_pdf == pdf_bytes


def test_list_auth_documents_returns_auth_documents_only():
    first_auth = create_auth(make_auth_payload())

    second_payload = make_auth_payload()
    second_payload["client_name"] = "Jane Smith"
    second_auth = create_auth(second_payload)

    first_document = create_auth_document(
        first_auth["id"],
        document_type="denial_letter",
        original_filename="denial.pdf",
        pdf_bytes=b"%PDF-1.7\ndenial",
    )
    create_auth_document(
        second_auth["id"],
        document_type="approval_letter",
        original_filename="approval.pdf",
        pdf_bytes=b"%PDF-1.7\napproval",
    )

    documents = list_auth_documents(first_auth["id"])

    assert documents == [first_document]


def test_create_auth_document_returns_none_for_missing_auth():
    assert (
        create_auth_document(
            999,
            document_type="approval_letter",
            original_filename="approval.pdf",
            pdf_bytes=b"%PDF-1.7\napproval",
        )
        is None
    )


def test_create_auth_document_rejects_invalid_type():
    auth = create_auth(make_auth_payload())

    with pytest.raises(InvalidAuthDocumentTypeError):
        create_auth_document(
            auth["id"],
            document_type="clinical_notes",
            original_filename="notes.pdf",
            pdf_bytes=b"%PDF-1.7\nnotes",
        )


def test_create_auth_document_rejects_non_pdf_bytes():
    auth = create_auth(make_auth_payload())

    with pytest.raises(InvalidAuthDocumentError):
        create_auth_document(
            auth["id"],
            document_type="approval_letter",
            original_filename="approval.txt",
            pdf_bytes=b"not a pdf",
        )


def test_create_auth_document_rejects_too_many_documents():
    auth = create_auth(make_auth_payload())

    for index in range(MAX_AUTH_DOCUMENTS_PER_AUTH):
        document = create_auth_document(
            auth["id"],
            document_type="other",
            original_filename=f"document-{index}.pdf",
            pdf_bytes=f"%PDF-1.7\ndocument {index}".encode(),
        )

        assert document is not None

    with pytest.raises(AuthDocumentLimitError):
        create_auth_document(
            auth["id"],
            document_type="other",
            original_filename="one-too-many.pdf",
            pdf_bytes=b"%PDF-1.7\nextra document",
        )


def test_create_auth_document_rejects_per_auth_storage_limit(monkeypatch):
    monkeypatch.setattr(
        "authstatus_api.authorizations.documents." "MAX_AUTH_DOCUMENT_BYTES_PER_AUTH",
        32,
    )

    auth = create_auth(make_auth_payload())

    create_auth_document(
        auth["id"],
        document_type="other",
        original_filename="first.pdf",
        pdf_bytes=b"%PDF-1.7\nfirst",
    )

    with pytest.raises(AuthDocumentLimitError):
        create_auth_document(
            auth["id"],
            document_type="other",
            original_filename="second.pdf",
            pdf_bytes=b"%PDF-1.7\nsecond file exceeds limit",
        )


def test_create_auth_document_rejects_global_storage_limit(monkeypatch):
    monkeypatch.setattr(
        "authstatus_api.authorizations.documents." "MAX_AUTH_DOCUMENT_BYTES_PER_AUTH",
        MAX_AUTH_DOCUMENT_BYTES_TOTAL,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.documents." "MAX_AUTH_DOCUMENT_BYTES_TOTAL",
        32,
    )

    first_auth = create_auth(make_auth_payload())

    second_payload = make_auth_payload()
    second_payload["client_name"] = "Jane Smith"
    second_auth = create_auth(second_payload)

    create_auth_document(
        first_auth["id"],
        document_type="other",
        original_filename="first.pdf",
        pdf_bytes=b"%PDF-1.7\nfirst",
    )

    with pytest.raises(AuthDocumentLimitError):
        create_auth_document(
            second_auth["id"],
            document_type="other",
            original_filename="second.pdf",
            pdf_bytes=b"%PDF-1.7\nsecond file exceeds global limit",
        )


def test_create_auth_document_truncates_long_filename():
    auth = create_auth(make_auth_payload())
    long_filename = f"{'a' * 220}.pdf"

    document = create_auth_document(
        auth["id"],
        document_type="other",
        original_filename=long_filename,
        pdf_bytes=b"%PDF-1.7\nletter",
    )

    assert document is not None
    assert len(document["original_filename"]) == 160


def test_delete_auth_document_removes_document_without_deleting_auth():
    auth = create_auth(make_auth_payload())
    document = create_auth_document(
        auth["id"],
        document_type="other",
        original_filename="letter.pdf",
        pdf_bytes=b"%PDF-1.7\nother",
    )

    assert delete_auth_document(auth["id"], document["id"]) is True
    assert get_auth_document(auth["id"], document["id"]) is None
    assert get_auth(auth["id"]) is not None


def test_delete_auth_document_returns_false_for_missing_document():
    auth = create_auth(make_auth_payload())

    assert delete_auth_document(auth["id"], 999) is False
