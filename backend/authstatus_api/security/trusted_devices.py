from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db
from authstatus_api.security.mappings import format_datetime
from authstatus_api.security.sessions import utc_now
from authstatus_api.settings import get_settings

TRUSTED_DEVICE_TOKEN_BYTES = 32
DEFAULT_TRUSTED_DEVICE_DAYS = 30

_TRUSTED_DEVICE_HMAC_INFO = b"carequeue:trusted-device-token:v1"


def generate_trusted_device_token() -> str:
    return secrets.token_urlsafe(TRUSTED_DEVICE_TOKEN_BYTES)


def _trusted_device_hmac_key() -> bytes:
    encryption_key = get_settings().encryption_key.strip()
    raw_key = base64.urlsafe_b64decode(encryption_key.encode("ascii"))

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_TRUSTED_DEVICE_HMAC_INFO,
    ).derive(raw_key)


def hash_trusted_device_token(token: str) -> str:
    return hmac.new(
        _trusted_device_hmac_key(),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_trusted_device(
    user_id: int,
    *,
    days: int = DEFAULT_TRUSTED_DEVICE_DAYS,
    ip_address: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    init_db()

    token = generate_trusted_device_token()
    token_hash = hash_trusted_device_token(token)
    now_datetime = utc_now()
    now = format_datetime(now_datetime)
    expires_at = format_datetime(now_datetime + timedelta(days=days))

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO trusted_devices (
                user_id,
                token_hash,
                created_at,
                last_used_at,
                expires_at,
                ip_address,
                user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                token_hash,
                now,
                now,
                expires_at,
                ip_address,
                user_agent,
            ),
        )

        trusted_device_id = cursor.lastrowid

    trusted_device = get_trusted_device_by_id(int(trusted_device_id))

    if trusted_device is None:
        raise RuntimeError("Unable to create trusted device.")

    return {
        "token": token,
        "trusted_device": trusted_device,
    }


def get_trusted_device_by_id(
    trusted_device_id: int,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM trusted_devices
            WHERE id = ?
            """,
            (trusted_device_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_active_trusted_device_by_token(
    token: str,
) -> dict[str, Any] | None:
    init_db()

    token_hash = hash_trusted_device_token(token)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM trusted_devices
            WHERE token_hash = ?
              AND revoked_at IS NULL
              AND expires_at > ?
            """,
            (
                token_hash,
                now,
            ),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def touch_trusted_device(token: str) -> bool:
    init_db()

    token_hash = hash_trusted_device_token(token)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE trusted_devices
            SET last_used_at = ?
            WHERE token_hash = ?
              AND revoked_at IS NULL
              AND expires_at > ?
            """,
            (
                now,
                token_hash,
                now,
            ),
        )

    return cursor.rowcount > 0


def revoke_trusted_device(token: str) -> bool:
    init_db()

    token_hash = hash_trusted_device_token(token)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE trusted_devices
            SET revoked_at = ?
            WHERE token_hash = ?
              AND revoked_at IS NULL
            """,
            (
                now,
                token_hash,
            ),
        )

    return cursor.rowcount > 0


def revoke_user_trusted_devices(user_id: int) -> int:
    init_db()

    now = format_datetime(utc_now())

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE trusted_devices
            SET revoked_at = ?
            WHERE user_id = ?
              AND revoked_at IS NULL
            """,
            (
                now,
                user_id,
            ),
        )

    return cursor.rowcount
