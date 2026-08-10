from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from authstatus_api.settings import get_settings

ENCRYPTED_TEXT_PREFIX = "enc:"


class EncryptionConfigError(RuntimeError):
    pass


class DecryptionError(RuntimeError):
    pass


ENCRYPTED_AUTH_FIELDS = {
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
}


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode("utf-8")


def get_fernet() -> Fernet:
    key = get_settings().encryption_key.strip()

    if not key:
        raise EncryptionConfigError("Missing AUTHSTATUS_ENCRYPTION_KEY.")

    try:
        return Fernet(key.encode("utf-8"))
    except ValueError as exc:
        raise EncryptionConfigError("Invalid AUTHSTATUS_ENCRYPTION_KEY.") from exc


def encrypt_text(value: str | None) -> str:
    if value is None:
        return ""

    clean_value = value.strip()

    if not clean_value:
        return ""

    if clean_value.startswith(ENCRYPTED_TEXT_PREFIX):
        return clean_value

    token = get_fernet().encrypt(clean_value.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTED_TEXT_PREFIX}{token}"


def decrypt_text(value: str | None) -> str:
    if value is None:
        return ""

    clean_value = value.strip()

    if not clean_value:
        return ""

    if not clean_value.startswith(ENCRYPTED_TEXT_PREFIX):
        return clean_value

    token = clean_value.removeprefix(ENCRYPTED_TEXT_PREFIX)

    try:
        return get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise DecryptionError("Unable to decrypt stored value.") from exc


def encrypt_auth_payload(payload: dict) -> dict:
    encrypted = payload.copy()

    for field in ENCRYPTED_AUTH_FIELDS:
        if field in encrypted:
            encrypted[field] = encrypt_text(encrypted[field])

    return encrypted


def decrypt_auth_record(record: dict) -> dict:
    decrypted = record.copy()

    for field in ENCRYPTED_AUTH_FIELDS:
        if field in decrypted:
            decrypted[field] = decrypt_text(decrypted[field])

    return decrypted
