from __future__ import annotations

import pytest

from authstatus_api.security.password_policy import (
    PASSWORD_POLICY_MESSAGE,
    PasswordPolicyError,
    validate_password_policy,
)


def test_validate_password_policy_accepts_long_passphrase():
    validate_password_policy("correct horse battery staple")


def test_validate_password_policy_rejects_short_password():
    with pytest.raises(
        PasswordPolicyError,
        match=PASSWORD_POLICY_MESSAGE,
    ):
        validate_password_policy("short")


def test_validate_password_policy_rejects_whitespace_only_password():
    with pytest.raises(
        PasswordPolicyError,
        match=PASSWORD_POLICY_MESSAGE,
    ):
        validate_password_policy(" " * 12)
