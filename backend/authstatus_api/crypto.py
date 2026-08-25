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
    "denial_reason_notes",
    "denial_prevention_notes",
    "p2p_reviewer",
    "p2p_notes",
    "appeal_notes",
    "retro_notes",
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


def get_previous_fernet() -> Fernet | None:
    key = get_settings().previous_encryption_key.strip()

    if not key:
        return None

    try:
        return Fernet(key.encode("utf-8"))
    except ValueError as exc:
        raise EncryptionConfigError(
            "Invalid AUTHSTATUS_PREVIOUS_ENCRYPTION_KEY."
        ) from exc


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
    token_bytes = token.encode("utf-8")

    try:
        return get_fernet().decrypt(token_bytes).decode("utf-8")
    except InvalidToken as current_key_error:
        previous_fernet = get_previous_fernet()

        if previous_fernet is None:
            raise DecryptionError(
                "Unable to decrypt stored value."
            ) from current_key_error

        try:
            return previous_fernet.decrypt(token_bytes).decode("utf-8")
        except InvalidToken as previous_key_error:
            raise DecryptionError(
                "Unable to decrypt stored value."
            ) from previous_key_error


def rotate_encrypted_text(value: str | None) -> tuple[str, bool]:
    if value is None:
        return "", False

    clean_value = value.strip()

    if not clean_value:
        return "", False

    if not clean_value.startswith(ENCRYPTED_TEXT_PREFIX):
        return clean_value, False

    token = clean_value.removeprefix(ENCRYPTED_TEXT_PREFIX)
    token_bytes = token.encode("utf-8")
    current_fernet = get_fernet()

    try:
        current_fernet.decrypt(token_bytes)
        return clean_value, False
    except InvalidToken:
        pass

    previous_fernet = get_previous_fernet()

    if previous_fernet is None:
        raise DecryptionError(
            "Unable to rotate stored value without a previous encryption key."
        )

    try:
        plaintext = previous_fernet.decrypt(token_bytes)
    except InvalidToken as exc:
        raise DecryptionError(
            "Unable to decrypt stored value during encryption key rotation."
        ) from exc

    rotated_token = current_fernet.encrypt(plaintext).decode("utf-8")

    return f"{ENCRYPTED_TEXT_PREFIX}{rotated_token}", True


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
