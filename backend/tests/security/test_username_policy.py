from __future__ import annotations

import pytest

from authstatus_api.security.username_policy import (
    USERNAME_POLICY_MESSAGE,
    UsernamePolicyError,
    normalize_username,
)
from authstatus_api.security.users import create_user
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("username", "expected"),
    [
        ("user@example.com", "user@example.com"),
        (" USER@EXAMPLE.COM ", "user@example.com"),
        ("user.name@example.com", "user.name@example.com"),
        ("user+tag@example.com", "user+tag@example.com"),
        ("user_name@example.co.uk", "user_name@example.co.uk"),
    ],
)
def test_normalize_username_accepts_valid_email_addresses(username, expected):
    assert normalize_username(username) == expected


@pytest.mark.parametrize(
    "username",
    [
        "",
        "admin",
        "admin@example",
        "@example.com",
        "admin@",
        "admin @example.com",
        "admin@example..com",
        "' OR 1=1 --",
        "admin@example.com'; DROP TABLE users; --",
    ],
)
def test_normalize_username_rejects_invalid_email_addresses(username):
    with pytest.raises(
        UsernamePolicyError,
        match=USERNAME_POLICY_MESSAGE,
    ):
        normalize_username(username)


def test_create_user_rejects_non_email_username():
    with pytest.raises(
        UsernamePolicyError,
        match=USERNAME_POLICY_MESSAGE,
    ):
        create_user(
            "admin",
            "correct horse battery staple",
            role="Admin",
        )


def test_create_user_rejects_sql_injection_shaped_username():
    with pytest.raises(
        UsernamePolicyError,
        match=USERNAME_POLICY_MESSAGE,
    ):
        create_user(
            "admin@example.com'; DROP TABLE users; --",
            "correct horse battery staple",
            role="Admin",
        )
