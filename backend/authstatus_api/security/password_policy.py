from __future__ import annotations

MINIMUM_PASSWORD_LENGTH = 12

PASSWORD_POLICY_MESSAGE = (
    f"Password must be at least {MINIMUM_PASSWORD_LENGTH} characters."
)


class PasswordPolicyError(ValueError):
    """Raised when a password does not satisfy CareQFlow password policy."""


def validate_password_policy(password: str) -> None:
    if len(password.strip()) < MINIMUM_PASSWORD_LENGTH:
        raise PasswordPolicyError(PASSWORD_POLICY_MESSAGE)
