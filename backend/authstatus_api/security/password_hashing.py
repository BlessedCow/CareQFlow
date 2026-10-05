from __future__ import annotations

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_password_hasher = PasswordHasher(type=Type.ID)

_DUMMY_PASSWORD_HASH = _password_hasher.hash(
    "CareQFlow authentication timing verification value"
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def perform_dummy_password_verification(password: str) -> None:
    verify_password(_DUMMY_PASSWORD_HASH, password)


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, VerificationError):
        return True
