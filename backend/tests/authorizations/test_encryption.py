from __future__ import annotations

from pathlib import Path

import pytest

from authstatus_api.authorizations.encryption import (
    back_up_and_encrypt_plaintext_authorization_fields,
    encrypt_plaintext_authorization_fields,
)
from authstatus_api.crypto import (
    ENCRYPTED_TEXT_PREFIX,
    decrypt_text,
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
