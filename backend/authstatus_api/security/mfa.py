from __future__ import annotations

import pyotp

from authstatus_api.crypto import decrypt_text, encrypt_text
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.security.mappings import format_datetime
from authstatus_api.security.sessions import utc_now

MFA_ISSUER_NAME = "CareQFlow"
TOTP_DIGITS = 6
TOTP_INTERVAL_SECONDS = 30


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def build_totp_provisioning_uri(
    username: str,
    secret: str,
) -> str:
    totp = pyotp.TOTP(
        secret,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL_SECONDS,
    )

    return totp.provisioning_uri(
        name=username.strip().lower(),
        issuer_name=MFA_ISSUER_NAME,
    )


def verify_totp_code(
    secret: str,
    code: str,
) -> bool:
    normalized_code = code.strip()

    if not normalized_code.isdigit():
        return False

    if len(normalized_code) != TOTP_DIGITS:
        return False

    totp = pyotp.TOTP(
        secret,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL_SECONDS,
    )

    return bool(
        totp.verify(
            normalized_code,
            valid_window=1,
        )
    )


def store_user_mfa_secret(
    user_id: int,
    secret: str,
) -> bool:
    init_db()

    encrypted_secret = encrypt_text(secret)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET
                mfa_secret = ?,
                mfa_enabled = 0,
                updated_at = ?
            WHERE id = ?
            """,
            (
                encrypted_secret,
                now,
                user_id,
            ),
        )

    return cursor.rowcount > 0


def get_user_mfa_secret(user_id: int) -> str | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT mfa_secret
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return None

    encrypted_secret = row["mfa_secret"]

    if not encrypted_secret:
        return None

    return decrypt_text(encrypted_secret)


def enable_user_mfa(user_id: int) -> bool:
    init_db()

    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET
                mfa_enabled = 1,
                updated_at = ?
            WHERE id = ?
              AND mfa_secret IS NOT NULL
            """,
            (
                now,
                user_id,
            ),
        )

    return cursor.rowcount > 0


def clear_user_mfa(user_id: int) -> bool:
    init_db()

    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE users
            SET
                mfa_enabled = 0,
                mfa_secret = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (
                now,
                user_id,
            ),
        )

    return cursor.rowcount > 0
