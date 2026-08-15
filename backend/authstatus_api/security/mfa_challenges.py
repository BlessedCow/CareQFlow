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
from authstatus_api.security.mappings import format_datetime, parse_datetime
from authstatus_api.security.sessions import utc_now
from authstatus_api.settings import get_settings

MFA_CHALLENGE_TOKEN_BYTES = 32
DEFAULT_MFA_CHALLENGE_MINUTES = 5

_MFA_CHALLENGE_HMAC_INFO = b"carequeue:mfa-challenge-token:v1"


def generate_mfa_challenge_token() -> str:
    return secrets.token_urlsafe(MFA_CHALLENGE_TOKEN_BYTES)


def _mfa_challenge_hmac_key() -> bytes:
    encryption_key = get_settings().encryption_key.strip()
    raw_key = base64.urlsafe_b64decode(encryption_key.encode("ascii"))

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_MFA_CHALLENGE_HMAC_INFO,
    ).derive(raw_key)


def hash_mfa_challenge_token(token: str) -> str:
    return hmac.new(
        _mfa_challenge_hmac_key(),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_mfa_login_challenge(
    user_id: int,
    *,
    minutes: int = DEFAULT_MFA_CHALLENGE_MINUTES,
    ip_address: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    init_db()

    token = generate_mfa_challenge_token()
    token_hash = hash_mfa_challenge_token(token)
    now_datetime = utc_now()
    now = format_datetime(now_datetime)
    expires_at = format_datetime(now_datetime + timedelta(minutes=minutes))

    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO mfa_login_challenges (
                user_id,
                token_hash,
                created_at,
                expires_at,
                ip_address,
                user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                token_hash,
                now,
                expires_at,
                ip_address,
                user_agent,
            ),
        )

        challenge_id = cursor.lastrowid

    challenge = get_mfa_login_challenge_by_id(int(challenge_id))

    if challenge is None:
        raise RuntimeError("Unable to create MFA login challenge.")

    return {
        "token": token,
        "challenge": challenge,
    }


def get_mfa_login_challenge_by_id(
    challenge_id: int,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM mfa_login_challenges
            WHERE id = ?
            """,
            (challenge_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def get_active_mfa_login_challenge_by_token(
    token: str,
) -> dict[str, Any] | None:
    init_db()

    token_hash = hash_mfa_challenge_token(token)
    now = format_datetime(utc_now())

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM mfa_login_challenges
            WHERE token_hash = ?
              AND consumed_at IS NULL
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


def consume_mfa_login_challenge(token: str) -> bool:
    init_db()

    token_hash = hash_mfa_challenge_token(token)
    now_datetime = utc_now()
    now = format_datetime(now_datetime)

    with get_conn() as conn:
        cursor = conn.execute(
            """
            UPDATE mfa_login_challenges
            SET consumed_at = ?
            WHERE token_hash = ?
              AND consumed_at IS NULL
              AND expires_at > ?
            """,
            (
                now,
                token_hash,
                now,
            ),
        )

    return cursor.rowcount > 0


def is_mfa_login_challenge_expired(challenge: dict[str, Any]) -> bool:
    return parse_datetime(challenge["expires_at"]) <= utc_now()
