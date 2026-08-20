from __future__ import annotations

import string

import pytest

from authstatus_api.audit.chain import (
    AUDIT_CHAIN_GENESIS,
    canonical_audit_event,
    hash_audit_chain_state,
    hash_audit_event,
)
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_audit_chain_test_settings(monkeypatch):
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def audit_event_values() -> dict:
    return {
        "event_id": 42,
        "user_id": 7,
        "username": "audit@example.com",
        "action": "auth.update",
        "resource_type": "auth",
        "resource_id": 123,
        "metadata": '{"fields": ["status"]}',
        "ip_address": "127.0.0.1",
        "user_agent": "CareQueue audit test",
        "created_at": "2026-08-19T12:00:00+00:00",
        "previous_hash": AUDIT_CHAIN_GENESIS,
    }


def test_canonical_audit_event_is_deterministic():
    values = audit_event_values()

    first = canonical_audit_event(**values)
    second = canonical_audit_event(**values)

    assert first == second


def test_hash_audit_event_is_deterministic_hmac_sha256_hex():
    values = audit_event_values()

    first_hash = hash_audit_event(**values)
    second_hash = hash_audit_event(**values)

    assert first_hash == second_hash
    assert len(first_hash) == 64
    assert all(character in string.hexdigits for character in first_hash)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("event_id", 43),
        ("user_id", 8),
        ("username", "other@example.com"),
        ("action", "auth.delete"),
        ("resource_type", "other"),
        ("resource_id", 124),
        ("metadata", '{"fields": ["status", "notes"]}'),
        ("ip_address", "127.0.0.2"),
        ("user_agent", "Different user agent"),
        ("created_at", "2026-08-19T12:00:01+00:00"),
        ("previous_hash", "different-previous-hash"),
    ],
)
def test_hash_audit_event_changes_when_protected_field_changes(
    field,
    replacement,
):
    original_values = audit_event_values()
    changed_values = {
        **original_values,
        field: replacement,
    }

    assert hash_audit_event(**original_values) != hash_audit_event(**changed_values)


def test_hash_audit_event_changes_when_encryption_key_changes(
    monkeypatch,
):
    values = audit_event_values()
    first_hash = hash_audit_event(**values)

    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    get_settings.cache_clear()

    second_hash = hash_audit_event(**values)

    assert first_hash != second_hash


def test_hash_audit_chain_state_is_deterministic():
    first_hash = hash_audit_chain_state(
        head_event_id=42,
        head_event_hash="a" * 64,
    )
    second_hash = hash_audit_chain_state(
        head_event_id=42,
        head_event_hash="a" * 64,
    )

    assert first_hash == second_hash
    assert len(first_hash) == 64
    assert all(character in string.hexdigits for character in first_hash)


@pytest.mark.parametrize(
    ("head_event_id", "head_event_hash"),
    [
        (43, "a" * 64),
        (42, "b" * 64),
    ],
)
def test_hash_audit_chain_state_changes_with_chain_head(
    head_event_id,
    head_event_hash,
):
    original_hash = hash_audit_chain_state(
        head_event_id=42,
        head_event_hash="a" * 64,
    )

    changed_hash = hash_audit_chain_state(
        head_event_id=head_event_id,
        head_event_hash=head_event_hash,
    )

    assert changed_hash != original_hash
