from __future__ import annotations

from pathlib import Path

from authstatus_api.backups.service import create_encrypted_database_backup
from authstatus_api.crypto import (
    ENCRYPTED_AUTH_FIELDS,
    ENCRYPTED_TEXT_PREFIX,
    encrypt_text,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db

AUTH_IDENTITY_FIELDS = {
    "client_name",
    "member_id",
    "group_number",
    "date_of_birth",
    "insurance_phone",
    "insurance_fax",
    "fax_numbers",
    "care_manager_details",
    "notes_links",
}


def encrypt_plaintext_authorization_fields() -> int:
    init_db()

    fields = sorted(AUTH_IDENTITY_FIELDS & ENCRYPTED_AUTH_FIELDS)
    select_columns = ", ".join(["id", *fields])

    with get_conn() as conn:
        rows = conn.execute(f"SELECT {select_columns} FROM auths").fetchall()  # nosec

        updated_rows = 0

        for row in rows:
            updates: dict[str, str] = {}

            for field in fields:
                value = row[field]

                if not isinstance(value, str):
                    continue

                clean_value = value.strip()

                if not clean_value:
                    continue

                if clean_value.startswith(ENCRYPTED_TEXT_PREFIX):
                    continue

                updates[field] = encrypt_text(clean_value)

            if not updates:
                continue

            assignments = ", ".join(f"{field} = ?" for field in updates)

            conn.execute(
                f"UPDATE auths SET {assignments} WHERE id = ?",  # nosec
                [*updates.values(), row["id"]],
            )
            updated_rows += 1

    return updated_rows


def back_up_and_encrypt_plaintext_authorization_fields() -> tuple[Path, int]:
    backup_path = create_encrypted_database_backup()
    updated_rows = encrypt_plaintext_authorization_fields()

    return backup_path, updated_rows
