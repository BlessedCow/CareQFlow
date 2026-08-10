from __future__ import annotations

from typing import Any, Literal

from cryptography.fernet import InvalidToken

from authstatus_api.authorizations.records import get_auth
from authstatus_api.authorizations.state import current_timestamp
from authstatus_api.crypto import DecryptionError, get_fernet
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db

ALLOWED_DOCUMENT_TYPES = {
    "auth_request",
    "approval_letter",
    "denial_letter",
    "other",
}

AuthDocumentType = Literal[
    "auth_request",
    "approval_letter",
    "denial_letter",
    "other",
]

PDF_CONTENT_TYPE = "application/pdf"
ENCRYPTED_BYTES_PREFIX = b"enc:"
DEFAULT_AUTH_DOCUMENT_FILENAME = "authorization-document.pdf"
MAX_AUTH_DOCUMENT_FILENAME_LENGTH = 160
MAX_AUTH_DOCUMENTS_PER_AUTH = 20
MAX_AUTH_DOCUMENT_BYTES_PER_AUTH = 50 * 1024 * 1024
MAX_AUTH_DOCUMENT_BYTES_TOTAL = 1024 * 1024 * 1024


class AuthDocumentError(ValueError):
    pass


class InvalidAuthDocumentTypeError(AuthDocumentError):
    pass


class InvalidAuthDocumentError(AuthDocumentError):
    pass


class AuthDocumentLimitError(AuthDocumentError):
    pass


def normalize_document_type(document_type: str) -> AuthDocumentType:
    normalized = document_type.strip().lower()

    if normalized not in ALLOWED_DOCUMENT_TYPES:
        raise InvalidAuthDocumentTypeError("Invalid authorization document type.")

    return normalized  # type: ignore[return-value]


def normalize_filename(filename: str | None) -> str:
    normalized = (filename or "").replace("\r", "").replace("\n", "").strip()

    if not normalized:
        return DEFAULT_AUTH_DOCUMENT_FILENAME

    return normalized[:MAX_AUTH_DOCUMENT_FILENAME_LENGTH]


def validate_pdf_document(pdf_bytes: bytes) -> None:
    if not pdf_bytes.startswith(b"%PDF"):
        raise InvalidAuthDocumentError("The uploaded document must be a PDF.")


def encrypt_pdf_bytes(pdf_bytes: bytes) -> bytes:
    if not pdf_bytes:
        raise InvalidAuthDocumentError("The uploaded PDF is empty.")

    if pdf_bytes.startswith(ENCRYPTED_BYTES_PREFIX):
        return pdf_bytes

    token = get_fernet().encrypt(pdf_bytes)
    return ENCRYPTED_BYTES_PREFIX + token


def decrypt_pdf_bytes(encrypted_pdf: bytes) -> bytes:
    if not encrypted_pdf:
        return b""

    if not encrypted_pdf.startswith(ENCRYPTED_BYTES_PREFIX):
        return encrypted_pdf

    token = encrypted_pdf.removeprefix(ENCRYPTED_BYTES_PREFIX)

    try:
        return get_fernet().decrypt(token)
    except InvalidToken as exc:
        raise DecryptionError("Unable to decrypt stored PDF.") from exc


def _document_row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "auth_id": row["auth_id"],
        "document_type": row["document_type"],
        "original_filename": row["original_filename"],
        "content_type": row["content_type"],
        "file_size_bytes": row["file_size_bytes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _get_auth_document_usage(conn: Any, auth_id: int) -> tuple[int, int]:
    row = conn.execute(
        """
        SELECT COUNT(*) AS document_count,
               COALESCE(SUM(file_size_bytes), 0) AS stored_bytes
        FROM auth_documents
        WHERE auth_id = ?
        """,
        (auth_id,),
    ).fetchone()

    return int(row["document_count"]), int(row["stored_bytes"])


def _get_total_auth_document_bytes(conn: Any) -> int:
    row = conn.execute("""
        SELECT COALESCE(SUM(file_size_bytes), 0) AS stored_bytes
        FROM auth_documents
        """).fetchone()

    return int(row["stored_bytes"])


def validate_auth_document_storage_limits(
    conn: Any,
    auth_id: int,
    *,
    file_size_bytes: int,
) -> None:
    document_count, auth_stored_bytes = _get_auth_document_usage(conn, auth_id)

    if document_count >= MAX_AUTH_DOCUMENTS_PER_AUTH:
        raise AuthDocumentLimitError(
            "The authorization already has the maximum number of documents."
        )

    if auth_stored_bytes + file_size_bytes > MAX_AUTH_DOCUMENT_BYTES_PER_AUTH:
        raise AuthDocumentLimitError(
            "The authorization document storage limit would be exceeded."
        )

    total_stored_bytes = _get_total_auth_document_bytes(conn)

    if total_stored_bytes + file_size_bytes > MAX_AUTH_DOCUMENT_BYTES_TOTAL:
        raise AuthDocumentLimitError(
            "The total authorization document storage limit would be exceeded."
        )


def list_auth_documents(auth_id: int) -> list[dict[str, Any]] | None:
    init_db()

    if get_auth(auth_id) is None:
        return None

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM auth_documents
            WHERE auth_id = ?
            ORDER BY id DESC
            """,
            (auth_id,),
        ).fetchall()

    return [_document_row_to_dict(row) for row in rows]


def create_auth_document(
    auth_id: int,
    *,
    document_type: str,
    original_filename: str | None,
    pdf_bytes: bytes,
) -> dict[str, Any] | None:
    init_db()

    if get_auth(auth_id) is None:
        return None

    normalized_document_type = normalize_document_type(document_type)
    normalized_filename = normalize_filename(original_filename)
    validate_pdf_document(pdf_bytes)
    file_size_bytes = len(pdf_bytes)

    with get_conn() as conn:
        validate_auth_document_storage_limits(
            conn,
            auth_id,
            file_size_bytes=file_size_bytes,
        )

        encrypted_pdf = encrypt_pdf_bytes(pdf_bytes)
        now = current_timestamp()

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
                normalized_document_type,
                normalized_filename,
                PDF_CONTENT_TYPE,
                encrypted_pdf,
                file_size_bytes,
                now,
                now,
            ),
        )

        document_id = int(cursor.lastrowid)
        row = conn.execute(
            """
            SELECT *
            FROM auth_documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

    return _document_row_to_dict(row)


def get_auth_document(
    auth_id: int,
    document_id: int,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM auth_documents
            WHERE id = ?
            AND auth_id = ?
            """,
            (document_id, auth_id),
        ).fetchone()

    if row is None:
        return None

    return _document_row_to_dict(row)


def get_auth_document_pdf(
    auth_id: int,
    document_id: int,
) -> tuple[dict[str, Any], bytes] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM auth_documents
            WHERE id = ?
            AND auth_id = ?
            """,
            (document_id, auth_id),
        ).fetchone()

    if row is None:
        return None

    document = _document_row_to_dict(row)
    return document, decrypt_pdf_bytes(row["encrypted_pdf"])


def delete_auth_document(
    auth_id: int,
    document_id: int,
) -> bool:
    init_db()

    with get_conn() as conn:
        cursor = conn.execute(
            """
            DELETE FROM auth_documents
            WHERE id = ?
            AND auth_id = ?
            """,
            (document_id, auth_id),
        )

    return cursor.rowcount > 0
