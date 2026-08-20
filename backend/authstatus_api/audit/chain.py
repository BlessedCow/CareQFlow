from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from authstatus_api.settings import get_settings

AUDIT_CHAIN_GENESIS = "carequeue:audit-chain:genesis:v1"

_AUDIT_CHAIN_HMAC_INFO = b"carequeue:audit-chain:v1"

_AUDIT_CHAIN_STATE_HMAC_INFO = b"carequeue:audit-chain-state:v1"


def _derive_audit_hmac_key(info: bytes) -> bytes:
    encryption_key = get_settings().encryption_key.strip()
    raw_key = base64.urlsafe_b64decode(encryption_key.encode("ascii"))

    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=info,
    ).derive(raw_key)


def _audit_chain_hmac_key() -> bytes:
    return _derive_audit_hmac_key(_AUDIT_CHAIN_HMAC_INFO)


def canonical_audit_event(
    *,
    event_id: int,
    user_id: int | None,
    username: str | None,
    action: str,
    resource_type: str,
    resource_id: int | None,
    metadata: str,
    ip_address: str,
    user_agent: str,
    created_at: str,
    previous_hash: str,
) -> str:
    payload: dict[str, Any] = {
        "id": event_id,
        "user_id": user_id,
        "username": username,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "metadata": metadata,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": created_at,
        "previous_hash": previous_hash,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def hash_audit_event(
    *,
    event_id: int,
    user_id: int | None,
    username: str | None,
    action: str,
    resource_type: str,
    resource_id: int | None,
    metadata: str,
    ip_address: str,
    user_agent: str,
    created_at: str,
    previous_hash: str,
) -> str:
    canonical_event = canonical_audit_event(
        event_id=event_id,
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=created_at,
        previous_hash=previous_hash,
    )

    return hmac.new(
        _audit_chain_hmac_key(),
        canonical_event.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hash_audit_chain_state(
    *,
    head_event_id: int,
    head_event_hash: str,
) -> str:
    payload = json.dumps(
        {
            "head_event_hash": head_event_hash,
            "head_event_id": head_event_id,
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    return hmac.new(
        _derive_audit_hmac_key(_AUDIT_CHAIN_STATE_HMAC_INFO),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
