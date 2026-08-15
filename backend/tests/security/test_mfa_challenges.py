from __future__ import annotations

import string

import pytest

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.security.mfa_challenges import (
    create_mfa_login_challenge,
    get_active_mfa_login_challenge_by_token,
    hash_mfa_challenge_token,
)
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_mfa_challenge_test_settings(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_hash_mfa_challenge_token_is_deterministic_hmac_sha256_hex():
    token = "challenge-token-value"

    first_hash = hash_mfa_challenge_token(token)
    second_hash = hash_mfa_challenge_token(token)

    assert first_hash == second_hash
    assert len(first_hash) == 64
    assert all(character in string.hexdigits for character in first_hash)
    assert first_hash != token


def test_hash_mfa_challenge_token_changes_when_token_changes():
    first_hash = hash_mfa_challenge_token("first-challenge-token")
    second_hash = hash_mfa_challenge_token("second-challenge-token")

    assert first_hash != second_hash


def test_mfa_challenge_can_be_retrieved_by_raw_token():
    user = create_user(
        "mfa-challenge@example.com",
        "correct horse battery staple",
        role="UR",
    )

    created = create_mfa_login_challenge(user["id"])

    challenge = get_active_mfa_login_challenge_by_token(created["token"])

    assert challenge is not None
    assert challenge["id"] == created["challenge"]["id"]
    assert challenge["token_hash"] == hash_mfa_challenge_token(created["token"])
    assert challenge["token_hash"] != created["token"]
