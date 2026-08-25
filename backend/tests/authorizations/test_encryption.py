from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from authstatus_api.authorizations.encryption import (
    FieldEncryptionRotationAuditError,
    back_up_and_encrypt_plaintext_authorization_fields,
    back_up_and_rotate_field_encryption_data,
    encrypt_plaintext_authorization_fields,
    rotate_field_encryption_data,
)
from authstatus_api.crypto import (
    ENCRYPTED_TEXT_PREFIX,
    DecryptionError,
    decrypt_text,
    encrypt_text,
    generate_encryption_key,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
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


def insert_authorization(**overrides) -> int:
    init_db()

    values = {
        "facility": "Example Facility",
        "client_name": "Example Patient",
        "member_id": "MEMBER123",
        "auth_number": "AUTH789",
        "group_number": "GROUP456",
        "date_of_birth": "1990-01-15",
        "loc": "RTC",
        "submission_methods": "Portal",
        "auth_type": "Initial",
        "status": "Pending",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    values.update(overrides)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO auths (
                facility,
                client_name,
                member_id,
                auth_number,
                group_number,
                date_of_birth,
                loc,
                submission_methods,
                auth_type,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values["facility"],
                values["client_name"],
                values["member_id"],
                values["auth_number"],
                values["group_number"],
                values["date_of_birth"],
                values["loc"],
                values["submission_methods"],
                values["auth_type"],
                values["status"],
                values["created_at"],
                values["updated_at"],
            ),
        )

    return int(cursor.lastrowid)


def configure_field_key_rotation(
    monkeypatch,
) -> tuple[str, str]:
    previous_key = generate_encryption_key()
    current_key = generate_encryption_key()

    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        current_key,
    )
    monkeypatch.setenv(
        "AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY",
        previous_key,
    )
    get_settings.cache_clear()

    return current_key, previous_key


def test_rotate_field_encryption_data_rotates_authorization_fields(
    monkeypatch,
):
    current_key, previous_key = configure_field_key_rotation(monkeypatch)

    legacy_fernet = Fernet(previous_key.encode("utf-8"))

    encrypted_client_name = ENCRYPTED_TEXT_PREFIX + legacy_fernet.encrypt(
        b"Example Patient"
    ).decode("utf-8")

    auth_id = insert_authorization(
        client_name=encrypted_client_name,
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )

    counts = rotate_field_encryption_data()

    assert counts == {
        "authorization_fields": 1,
        "event_notes": 0,
        "mfa_secrets": 0,
        "documents": 0,
    }

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT client_name
            FROM auths
            WHERE id = ?
            """,
            (auth_id,),
        ).fetchone()

    assert row is not None
    assert row["client_name"] != encrypted_client_name

    current_fernet = Fernet(current_key.encode("utf-8"))
    rotated_token = (
        row["client_name"].removeprefix(ENCRYPTED_TEXT_PREFIX).encode("utf-8")
    )

    assert current_fernet.decrypt(rotated_token) == b"Example Patient"


def test_rotate_field_encryption_data_skips_current_key_values(
    monkeypatch,
):
    configure_field_key_rotation(monkeypatch)

    encrypted_client_name = encrypt_text("Example Patient")

    insert_authorization(
        client_name=encrypted_client_name,
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )

    counts = rotate_field_encryption_data()

    assert counts == {
        "authorization_fields": 0,
        "event_notes": 0,
        "mfa_secrets": 0,
        "documents": 0,
    }


def test_rotate_field_encryption_data_rolls_back_on_failure(
    monkeypatch,
):
    _, previous_key = configure_field_key_rotation(monkeypatch)
    unknown_key = generate_encryption_key()

    previous_fernet = Fernet(previous_key.encode("utf-8"))
    unknown_fernet = Fernet(unknown_key.encode("utf-8"))

    first_value = ENCRYPTED_TEXT_PREFIX + previous_fernet.encrypt(
        b"First Patient"
    ).decode("utf-8")
    invalid_value = ENCRYPTED_TEXT_PREFIX + unknown_fernet.encrypt(
        b"Second Patient"
    ).decode("utf-8")

    first_id = insert_authorization(
        client_name=first_value,
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )
    insert_authorization(
        client_name=invalid_value,
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )

    with pytest.raises(
        DecryptionError,
        match="during encryption key rotation",
    ):
        rotate_field_encryption_data()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT client_name
            FROM auths
            WHERE id = ?
            """,
            (first_id,),
        ).fetchone()

    assert row is not None
    assert row["client_name"] == first_value


def test_rotate_field_encryption_data_rotates_event_notes(
    monkeypatch,
):
    current_key, previous_key = configure_field_key_rotation(monkeypatch)
    previous_fernet = Fernet(previous_key.encode("utf-8"))

    auth_id = insert_authorization(
        client_name="",
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )

    encrypted_notes = ENCRYPTED_TEXT_PREFIX + previous_fernet.encrypt(
        b"Legacy event note"
    ).decode("utf-8")

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO auth_events (
                auth_id,
                event_type,
                event_date,
                notes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                auth_id,
                "note",
                "2026-01-01",
                encrypted_notes,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        event_id = cursor.lastrowid

    counts = rotate_field_encryption_data()

    assert counts == {
        "authorization_fields": 0,
        "event_notes": 1,
        "mfa_secrets": 0,
        "documents": 0,
    }

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT notes
            FROM auth_events
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()

    assert row is not None
    assert row["notes"] != encrypted_notes

    token = row["notes"].removeprefix(ENCRYPTED_TEXT_PREFIX).encode("utf-8")

    current_fernet = Fernet(current_key.encode("utf-8"))

    assert current_fernet.decrypt(token) == b"Legacy event note"


def test_rotate_field_encryption_data_rotates_mfa_secret(
    monkeypatch,
):
    current_key, previous_key = configure_field_key_rotation(monkeypatch)
    init_db()
    previous_fernet = Fernet(previous_key.encode("utf-8"))

    encrypted_secret = ENCRYPTED_TEXT_PREFIX + previous_fernet.encrypt(
        b"JBSWY3DPEHPK3PXP"
    ).decode("utf-8")

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                password_changed_at,
                mfa_secret,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "rotation-test-user",
                "not-a-real-password-hash",
                "Read Only",
                "2026-01-01T00:00:00+00:00",
                encrypted_secret,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        user_id = cursor.lastrowid

    counts = rotate_field_encryption_data()

    assert counts == {
        "authorization_fields": 0,
        "event_notes": 0,
        "mfa_secrets": 1,
        "documents": 0,
    }

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT mfa_secret
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    assert row is not None
    assert row["mfa_secret"] != encrypted_secret

    token = row["mfa_secret"].removeprefix(ENCRYPTED_TEXT_PREFIX).encode("utf-8")

    current_fernet = Fernet(current_key.encode("utf-8"))

    assert current_fernet.decrypt(token) == b"JBSWY3DPEHPK3PXP"


def test_rotate_field_encryption_data_rotates_document(
    monkeypatch,
):
    current_key, previous_key = configure_field_key_rotation(monkeypatch)
    previous_fernet = Fernet(previous_key.encode("utf-8"))

    auth_id = insert_authorization(
        client_name="",
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )

    pdf_bytes = b"%PDF-1.7\nlegacy document"
    encrypted_pdf = b"enc:" + previous_fernet.encrypt(pdf_bytes)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO auth_documents (
                auth_id,
                document_type,
                original_filename,
                content_type,
                encrypted_pdf,
                file_size_bytes,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                auth_id,
                "authorization",
                "legacy.pdf",
                "application/pdf",
                encrypted_pdf,
                len(pdf_bytes),
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        document_id = cursor.lastrowid

    counts = rotate_field_encryption_data()

    assert counts == {
        "authorization_fields": 0,
        "event_notes": 0,
        "mfa_secrets": 0,
        "documents": 1,
    }

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT encrypted_pdf
            FROM auth_documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

    assert row is not None

    rotated_pdf = bytes(row["encrypted_pdf"])
    assert rotated_pdf != encrypted_pdf

    token = rotated_pdf.removeprefix(b"enc:")
    current_fernet = Fernet(current_key.encode("utf-8"))

    assert current_fernet.decrypt(token) == pdf_bytes


def test_rotate_field_encryption_data_rolls_back_when_verification_fails(
    monkeypatch,
):
    _, previous_key = configure_field_key_rotation(monkeypatch)
    previous_fernet = Fernet(previous_key.encode("utf-8"))

    original_value = ENCRYPTED_TEXT_PREFIX + previous_fernet.encrypt(
        b"Example Patient"
    ).decode("utf-8")

    auth_id = insert_authorization(
        client_name=original_value,
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )

    def fail_verification(
        conn,
        *,
        fields,
    ) -> None:
        raise DecryptionError("forced verification failure")

    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption."
        "_verify_field_encryption_uses_current_key",
        fail_verification,
    )

    with pytest.raises(
        DecryptionError,
        match="forced verification failure",
    ):
        rotate_field_encryption_data()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT client_name
            FROM auths
            WHERE id = ?
            """,
            (auth_id,),
        ).fetchone()

    assert row is not None
    assert row["client_name"] == original_value


def test_field_rotation_verification_requires_current_key(
    monkeypatch,
):
    _, previous_key = configure_field_key_rotation(monkeypatch)
    previous_fernet = Fernet(previous_key.encode("utf-8"))

    legacy_value = ENCRYPTED_TEXT_PREFIX + previous_fernet.encrypt(
        b"Example Patient"
    ).decode("utf-8")

    insert_authorization(
        client_name=legacy_value,
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )

    def leave_value_unrotated(
        value,
    ):
        return value, False

    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "rotate_encrypted_text",
        leave_value_unrotated,
    )

    with pytest.raises(
        DecryptionError,
        match="failed current-key verification",
    ):
        rotate_field_encryption_data()


def test_failed_field_key_rotation_does_not_write_success_audit(
    monkeypatch,
    tmp_path,
):
    audit_called = False
    backup_path = tmp_path / "auth_tracker.db.enc"

    def create_backup() -> Path:
        return backup_path

    def verify_backup(*, backup_path: Path) -> None:
        return None

    def rotate_fields() -> dict[str, int]:
        raise DecryptionError("rotation failed")

    def record_event(**kwargs) -> dict:
        nonlocal audit_called
        audit_called = True
        return {}

    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "create_encrypted_database_backup",
        create_backup,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "verify_encrypted_database_backup",
        verify_backup,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "rotate_field_encryption_data",
        rotate_fields,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "record_audit_event",
        record_event,
    )

    with pytest.raises(
        DecryptionError,
        match="rotation failed",
    ):
        back_up_and_rotate_field_encryption_data(
            username="rotation-admin",
        )

    assert audit_called is False


def test_audit_failure_reports_rotation_as_completed(
    monkeypatch,
    tmp_path,
):
    backup_path = tmp_path / "auth_tracker.db.enc"
    counts = {
        "authorization_fields": 2,
        "event_notes": 1,
        "mfa_secrets": 1,
        "documents": 1,
    }

    def create_backup() -> Path:
        return backup_path

    def verify_backup(*, backup_path: Path) -> None:
        return None

    def rotate_fields() -> dict[str, int]:
        return counts

    def record_event(**kwargs) -> dict:
        raise RuntimeError("audit chain unavailable")

    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "create_encrypted_database_backup",
        create_backup,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "verify_encrypted_database_backup",
        verify_backup,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "rotate_field_encryption_data",
        rotate_fields,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "record_audit_event",
        record_event,
    )

    with pytest.raises(
        FieldEncryptionRotationAuditError,
        match=(
            "rotation completed successfully, "
            "but the security audit event could not be recorded"
        ),
    ) as exc_info:
        back_up_and_rotate_field_encryption_data(
            username="rotation-admin",
        )

    assert exc_info.value.backup_path == backup_path
    assert exc_info.value.counts == counts


def test_encrypt_plaintext_authorization_fields_encrypts_identity_values():
    auth_id = insert_authorization()

    updated_rows = encrypt_plaintext_authorization_fields()

    assert updated_rows == 1

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT client_name, member_id, auth_number, group_number, date_of_birth
            FROM auths
            WHERE id = ?
            """,
            (auth_id,),
        ).fetchone()

    assert row is not None

    for field in (
        "client_name",
        "member_id",
        "auth_number",
        "group_number",
        "date_of_birth",
    ):
        assert row[field].startswith(ENCRYPTED_TEXT_PREFIX)

    assert decrypt_text(row["client_name"]) == "Example Patient"
    assert decrypt_text(row["member_id"]) == "MEMBER123"
    assert decrypt_text(row["auth_number"]) == "AUTH789"
    assert decrypt_text(row["group_number"]) == "GROUP456"
    assert decrypt_text(row["date_of_birth"]) == "1990-01-15"


def test_encrypt_plaintext_authorization_fields_is_idempotent():
    insert_authorization()

    assert encrypt_plaintext_authorization_fields() == 1
    assert encrypt_plaintext_authorization_fields() == 0


def test_encrypt_plaintext_authorization_fields_skips_empty_values():
    auth_id = insert_authorization(
        member_id="",
        auth_number="",
        group_number="",
        date_of_birth="",
    )

    assert encrypt_plaintext_authorization_fields() == 1

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT member_id, auth_number, group_number, date_of_birth
            FROM auths
            WHERE id = ?
            """,
            (auth_id,),
        ).fetchone()

    assert row is not None
    assert row["member_id"] == ""
    assert row["auth_number"] == ""
    assert row["group_number"] == ""
    assert row["date_of_birth"] == ""


def test_backup_runs_before_authorization_encryption(monkeypatch, tmp_path):
    calls: list[str] = []
    backup_path = tmp_path / "auth_tracker.db.enc"

    def create_backup() -> Path:
        calls.append("backup")
        return backup_path

    def encrypt_fields() -> int:
        calls.append("encrypt")
        return 3

    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption.create_encrypted_database_backup",
        create_backup,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption."
        "encrypt_plaintext_authorization_fields",
        encrypt_fields,
    )

    result = back_up_and_encrypt_plaintext_authorization_fields()

    assert result == (backup_path, 3)
    assert calls == ["backup", "encrypt"]


def test_backup_failure_prevents_authorization_encryption(monkeypatch):
    encryption_called = False

    def create_backup() -> Path:
        raise RuntimeError("backup failed")

    def encrypt_fields() -> int:
        nonlocal encryption_called
        encryption_called = True
        return 1

    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption.create_encrypted_database_backup",
        create_backup,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption."
        "encrypt_plaintext_authorization_fields",
        encrypt_fields,
    )

    with pytest.raises(RuntimeError, match="backup failed"):
        back_up_and_encrypt_plaintext_authorization_fields()

    assert encryption_called is False


def test_backup_verification_rotation_and_audit_run_in_order(
    monkeypatch,
    tmp_path,
):
    calls: list[str] = []
    backup_path = tmp_path / "auth_tracker.db.enc"

    counts = {
        "authorization_fields": 2,
        "event_notes": 1,
        "mfa_secrets": 1,
        "documents": 1,
    }

    def create_backup() -> Path:
        calls.append("backup")
        return backup_path

    def verify_backup(*, backup_path: Path) -> None:
        calls.append("verify")

    def rotate_fields() -> dict[str, int]:
        calls.append("rotate")
        return counts

    def record_event(**kwargs) -> dict:
        calls.append("audit")

        assert kwargs == {
            "action": "security.field_encryption_key_rotated",
            "resource_type": "security",
            "username": "rotation-admin",
            "metadata": counts,
        }

        return {}

    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "create_encrypted_database_backup",
        create_backup,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "verify_encrypted_database_backup",
        verify_backup,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "rotate_field_encryption_data",
        rotate_fields,
    )
    monkeypatch.setattr(
        "authstatus_api.authorizations.encryption." "record_audit_event",
        record_event,
    )

    result = back_up_and_rotate_field_encryption_data(
        username="rotation-admin",
    )

    assert result == (
        backup_path,
        counts,
    )
    assert calls == [
        "backup",
        "verify",
        "rotate",
        "audit",
    ]
