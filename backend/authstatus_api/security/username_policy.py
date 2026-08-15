from __future__ import annotations

from pydantic import EmailStr, TypeAdapter, ValidationError

USERNAME_POLICY_MESSAGE = "Username must be a valid email address."

_EMAIL_ADAPTER = TypeAdapter(EmailStr)


class UsernamePolicyError(ValueError):
    pass


def normalize_username(username: str) -> str:
    try:
        validated_username = _EMAIL_ADAPTER.validate_python(username.strip())
    except ValidationError as exc:
        raise UsernamePolicyError(USERNAME_POLICY_MESSAGE) from exc

    return str(validated_username).lower()
