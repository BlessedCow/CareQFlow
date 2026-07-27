from __future__ import annotations

from authstatus_api.security.password_hashing import (
    hash_password,
    password_needs_rehash,
    verify_password,
)


def test_hash_password_creates_argon2id_hash():
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert password_hash.startswith("$argon2id$")


def test_verify_password_accepts_correct_password():
    password_hash = hash_password("correct horse battery staple")

    assert verify_password(password_hash, "correct horse battery staple") is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password("correct horse battery staple")

    assert verify_password(password_hash, "wrong password") is False


def test_verify_password_rejects_invalid_hash():
    assert verify_password("not-a-real-hash", "password") is False


def test_password_needs_rehash_handles_current_hash():
    password_hash = hash_password("correct horse battery staple")

    assert password_needs_rehash(password_hash) is False


def test_password_needs_rehash_rejects_invalid_hash():
    assert password_needs_rehash("not-a-real-hash") is True