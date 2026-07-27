from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from authstatus_api import crypto
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_generate_encryption_key_creates_valid_fernet_key():
    key = crypto.generate_encryption_key()

    Fernet(key.encode("utf-8"))


def test_encrypt_text_requires_key(monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", "")

    with pytest.raises(crypto.EncryptionConfigError):
        crypto.encrypt_text("John Smith")


def test_encrypt_and_decrypt_text(monkeypatch):
    key = crypto.generate_encryption_key()
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", key)

    encrypted = crypto.encrypt_text("John Smith")

    assert encrypted.startswith(crypto.ENCRYPTED_TEXT_PREFIX)
    assert "John Smith" not in encrypted
    assert crypto.decrypt_text(encrypted) == "John Smith"


def test_encrypt_text_ignores_empty_values(monkeypatch):
    key = crypto.generate_encryption_key()
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", key)

    assert crypto.encrypt_text(None) == ""
    assert crypto.encrypt_text("") == ""
    assert crypto.encrypt_text("   ") == ""


def test_encrypt_text_does_not_double_encrypt(monkeypatch):
    key = crypto.generate_encryption_key()
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", key)

    encrypted = crypto.encrypt_text("ABC123")

    assert crypto.encrypt_text(encrypted) == encrypted


def test_decrypt_text_returns_plaintext_values(monkeypatch):
    key = crypto.generate_encryption_key()
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", key)

    assert crypto.decrypt_text("ABC123") == "ABC123"


def test_encrypt_auth_payload_encrypts_selected_fields(monkeypatch):
    key = crypto.generate_encryption_key()
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", key)

    payload = {
        "client_name": "John Smith",
        "member_id": "ABC123",
        "facility": "Facility A",
        "loc": "RTC",
        "status": "In Progress",
    }

    encrypted = crypto.encrypt_auth_payload(payload)

    assert encrypted["client_name"].startswith(crypto.ENCRYPTED_TEXT_PREFIX)
    assert encrypted["member_id"].startswith(crypto.ENCRYPTED_TEXT_PREFIX)
    assert encrypted["facility"] == "Facility A"
    assert encrypted["loc"] == "RTC"
    assert encrypted["status"] == "In Progress"


def test_decrypt_auth_record_decrypts_selected_fields(monkeypatch):
    key = crypto.generate_encryption_key()
    monkeypatch.setenv("AUTHSTATUS_ENCRYPTION_KEY", key)

    encrypted = crypto.encrypt_auth_payload(
        {
            "client_name": "John Smith",
            "member_id": "ABC123",
            "facility": "Facility A",
            "loc": "RTC",
        }
    )

    decrypted = crypto.decrypt_auth_record(encrypted)

    assert decrypted["client_name"] == "John Smith"
    assert decrypted["member_id"] == "ABC123"
    assert decrypted["facility"] == "Facility A"
    assert decrypted["loc"] == "RTC"