from __future__ import annotations

from pathlib import Path

from cryptography.fernet import InvalidToken

from authstatus_api.audit.service import record_audit_event
from authstatus_api.authorizations.documents import (
    ENCRYPTED_BYTES_PREFIX,
    rotate_encrypted_pdf_bytes,
)
from authstatus_api.backups.service import (
    create_encrypted_database_backup,
    verify_encrypted_database_backup,
)
from authstatus_api.crypto import (
    ENCRYPTED_AUTH_FIELDS,
    ENCRYPTED_TEXT_PREFIX,
    DecryptionError,
    EncryptionConfigError,
    encrypt_text,
    get_fernet,
    get_previous_fernet,
    rotate_encrypted_text,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db

AUTH_IDENTITY_FIELDS = {
    "client_name",
    "member_id",
    "auth_number",
    "group_number",
    "date_of_birth",
    "insurance_phone",
    "insurance_fax",
    "fax_numbers",
    "care_manager_details",
    "notes_links",
    "denial_reason_notes",
    "denial_prevention_notes",
    "p2p_reviewer",
    "p2p_notes",
    "appeal_notes",
    "retro_notes",
}

FIELD_ROTATION_COUNT_KEYS = (
    "authorization_fields",
    "event_notes",
    "mfa_secrets",
    "documents",
)


class FieldEncryptionRotationAuditError(RuntimeError):
    def __init__(
        self,
        *,
        backup_path: Path,
        counts: dict[str, int],
    ) -> None:
        super().__init__(
            "Field encryption key rotation completed successfully, "
            "but the security audit event could not be recorded."
        )
        self.backup_path = backup_path
        self.counts = counts


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


def _verify_field_encryption_uses_current_key(
    conn,
    *,
    fields: list[str],
) -> None:
    current_fernet = get_fernet()
    select_columns = ", ".join(["id", *fields])

    auth_rows = conn.execute(f"SELECT {select_columns} FROM auths").fetchall()  # nosec

    for row in auth_rows:
        for field in fields:
            value = row[field]

            if value is None:
                continue

            if not isinstance(value, str):
                raise DecryptionError(
                    "Field encryption verification encountered an invalid "
                    "authorization field value."
                )

            clean_value = value.strip()

            if not clean_value:
                continue

            if not clean_value.startswith(ENCRYPTED_TEXT_PREFIX):
                raise DecryptionError(
                    "Field encryption verification encountered unencrypted "
                    "authorization data."
                )

            token = clean_value.removeprefix(ENCRYPTED_TEXT_PREFIX).encode("utf-8")

            try:
                current_fernet.decrypt(token)
            except InvalidToken as exc:
                raise DecryptionError(
                    "Authorization data failed current-key verification."
                ) from exc

    event_rows = conn.execute("""
        SELECT notes
        FROM auth_events
        WHERE notes IS NOT NULL
          AND notes != ''
        """).fetchall()

    for row in event_rows:
        notes = row["notes"]

        if not isinstance(notes, str):
            raise DecryptionError(
                "Field encryption verification encountered an invalid "
                "authorization event note."
            )

        clean_notes = notes.strip()

        if not clean_notes:
            continue

        if not clean_notes.startswith(ENCRYPTED_TEXT_PREFIX):
            raise DecryptionError(
                "Field encryption verification encountered unencrypted "
                "authorization event data."
            )

        token = clean_notes.removeprefix(ENCRYPTED_TEXT_PREFIX).encode("utf-8")

        try:
            current_fernet.decrypt(token)
        except InvalidToken as exc:
            raise DecryptionError(
                "Authorization event data failed current-key verification."
            ) from exc

    user_rows = conn.execute("""
        SELECT mfa_secret
        FROM users
        WHERE mfa_secret IS NOT NULL
          AND mfa_secret != ''
        """).fetchall()

    for row in user_rows:
        mfa_secret = row["mfa_secret"]

        if not isinstance(mfa_secret, str):
            raise DecryptionError(
                "Field encryption verification encountered an invalid " "MFA secret."
            )

        clean_secret = mfa_secret.strip()

        if not clean_secret:
            continue

        if not clean_secret.startswith(ENCRYPTED_TEXT_PREFIX):
            raise DecryptionError(
                "Field encryption verification encountered an unencrypted "
                "MFA secret."
            )

        token = clean_secret.removeprefix(ENCRYPTED_TEXT_PREFIX).encode("utf-8")

        try:
            current_fernet.decrypt(token)
        except InvalidToken as exc:
            raise DecryptionError(
                "MFA secret failed current-key verification."
            ) from exc

    document_rows = conn.execute("""
        SELECT encrypted_pdf
        FROM auth_documents
        """).fetchall()

    for row in document_rows:
        encrypted_pdf = row["encrypted_pdf"]

        if encrypted_pdf is None:
            raise DecryptionError(
                "Field encryption verification encountered a missing "
                "authorization document."
            )

        pdf_bytes = bytes(encrypted_pdf)

        if not pdf_bytes.startswith(ENCRYPTED_BYTES_PREFIX):
            raise DecryptionError(
                "Field encryption verification encountered an unencrypted "
                "authorization document."
            )

        token = pdf_bytes.removeprefix(ENCRYPTED_BYTES_PREFIX)

        try:
            current_fernet.decrypt(token)
        except InvalidToken as exc:
            raise DecryptionError(
                "Authorization document failed current-key verification."
            ) from exc


def rotate_field_encryption_data() -> dict[str, int]:
    init_db()

    if get_previous_fernet() is None:
        raise EncryptionConfigError(
            "AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY is required "
            "for field encryption key rotation."
        )

    fields = sorted(AUTH_IDENTITY_FIELDS & ENCRYPTED_AUTH_FIELDS)
    select_columns = ", ".join(["id", *fields])

    counts = {key: 0 for key in FIELD_ROTATION_COUNT_KEYS}

    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")

        auth_rows = conn.execute(
            f"SELECT {select_columns} FROM auths"  # nosec
        ).fetchall()

        for row in auth_rows:
            updates: dict[str, str] = {}

            for field in fields:
                value = row[field]

                if value is None:
                    continue

                if not isinstance(value, str):
                    raise DecryptionError(
                        "Field encryption rotation encountered an invalid "
                        "authorization field value."
                    )

                clean_value = value.strip()

                if not clean_value:
                    continue

                if not clean_value.startswith(ENCRYPTED_TEXT_PREFIX):
                    raise DecryptionError(
                        "Field encryption rotation encountered unencrypted "
                        "authorization data."
                    )

                rotated_value, changed = rotate_encrypted_text(clean_value)

                if not changed:
                    continue

                updates[field] = rotated_value
                counts["authorization_fields"] += 1

            if updates:
                assignments = ", ".join(f"{field} = ?" for field in updates)

                conn.execute(
                    f"UPDATE auths SET {assignments} WHERE id = ?",  # nosec
                    [*updates.values(), row["id"]],
                )

        event_rows = conn.execute("""
            SELECT id, notes
            FROM auth_events
            WHERE notes IS NOT NULL
              AND notes != ''
            """).fetchall()

        for row in event_rows:
            notes = row["notes"]

            if not isinstance(notes, str):
                raise DecryptionError(
                    "Field encryption rotation encountered an invalid "
                    "authorization event note."
                )

            clean_notes = notes.strip()

            if not clean_notes:
                continue

            if not clean_notes.startswith(ENCRYPTED_TEXT_PREFIX):
                raise DecryptionError(
                    "Field encryption rotation encountered unencrypted "
                    "authorization event data."
                )

            rotated_notes, changed = rotate_encrypted_text(clean_notes)

            if not changed:
                continue

            conn.execute(
                """
                UPDATE auth_events
                SET notes = ?
                WHERE id = ?
                """,
                (
                    rotated_notes,
                    row["id"],
                ),
            )
            counts["event_notes"] += 1

        user_rows = conn.execute("""
            SELECT id, mfa_secret
            FROM users
            WHERE mfa_secret IS NOT NULL
              AND mfa_secret != ''
            """).fetchall()

        for row in user_rows:
            mfa_secret = row["mfa_secret"]

            if not isinstance(mfa_secret, str):
                raise DecryptionError(
                    "Field encryption rotation encountered an invalid " "MFA secret."
                )

            clean_secret = mfa_secret.strip()

            if not clean_secret:
                continue

            if not clean_secret.startswith(ENCRYPTED_TEXT_PREFIX):
                raise DecryptionError(
                    "Field encryption rotation encountered an unencrypted "
                    "MFA secret."
                )

            rotated_secret, changed = rotate_encrypted_text(clean_secret)

            if not changed:
                continue

            conn.execute(
                """
                UPDATE users
                SET mfa_secret = ?
                WHERE id = ?
                """,
                (
                    rotated_secret,
                    row["id"],
                ),
            )
            counts["mfa_secrets"] += 1

        document_rows = conn.execute("""
            SELECT id, encrypted_pdf
            FROM auth_documents
            """).fetchall()

        for row in document_rows:
            encrypted_pdf = row["encrypted_pdf"]

            if encrypted_pdf is None:
                raise DecryptionError(
                    "Field encryption rotation encountered a missing "
                    "authorization document."
                )

            pdf_bytes = bytes(encrypted_pdf)

            if not pdf_bytes.startswith(ENCRYPTED_BYTES_PREFIX):
                raise DecryptionError(
                    "Field encryption rotation encountered an unencrypted "
                    "authorization document."
                )

            rotated_pdf, changed = rotate_encrypted_pdf_bytes(pdf_bytes)

            if not changed:
                continue

            conn.execute(
                """
                UPDATE auth_documents
                SET encrypted_pdf = ?
                WHERE id = ?
                """,
                (
                    rotated_pdf,
                    row["id"],
                ),
            )
            counts["documents"] += 1

        _verify_field_encryption_uses_current_key(
            conn,
            fields=fields,
        )

    return counts


def back_up_and_rotate_field_encryption_data(
    *,
    username: str | None = None,
) -> tuple[Path, dict[str, int]]:
    backup_path = create_encrypted_database_backup()

    verify_encrypted_database_backup(
        backup_path=backup_path,
    )

    counts = rotate_field_encryption_data()

    try:
        record_audit_event(
            action="security.field_encryption_key_rotated",
            resource_type="security",
            username=username,
            metadata={
                "authorization_fields": counts["authorization_fields"],
                "event_notes": counts["event_notes"],
                "mfa_secrets": counts["mfa_secrets"],
                "documents": counts["documents"],
            },
        )
    except Exception as exc:
        raise FieldEncryptionRotationAuditError(
            backup_path=backup_path,
            counts=counts,
        ) from exc

    return backup_path, counts


def back_up_and_encrypt_plaintext_authorization_fields() -> tuple[Path, int]:
    backup_path = create_encrypted_database_backup()
    updated_rows = encrypt_plaintext_authorization_fields()

    return backup_path, updated_rows
