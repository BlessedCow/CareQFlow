from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED_VALUE = "[REDACTED]"

SENSITIVE_FIELD_NAMES = {
    "auth_number",
    "authorization",
    "authorization_header",
    "behavioral_health_group_number",
    "behavioral_health_member_id",
    "bh_group_number",
    "bh_member_id",
    "cookie",
    "cookies",
    "csrf_token",
    "date_of_birth",
    "dob",
    "group_number",
    "medical_group_number",
    "medical_member_id",
    "member_id",
    "password",
    "password_hash",
    "session",
    "session_id",
    "session_token",
    "set_cookie",
    "token",
    "token_hash",
}

SENSITIVE_FIELD_SUFFIXES = (
    "_password",
    "_secret",
    "_token",
    "_token_hash",
)

AUTHORIZATION_HEADER_PATTERN = re.compile(
    r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+",
    re.IGNORECASE,
)

COOKIE_VALUE_PATTERN = re.compile(
    r"(?i)\b("
    r"carequeue_session"
    r"|session"
    r"|sessionid"
    r"|csrf"
    r"|csrf_token"
    r")=([^;\s]+)"
)


def normalize_field_name(field_name: object) -> str:
    return str(field_name).strip().lower().replace("-", "_")


def is_sensitive_field(field_name: object) -> bool:
    normalized_name = normalize_field_name(field_name)

    return normalized_name in SENSITIVE_FIELD_NAMES or normalized_name.endswith(
        SENSITIVE_FIELD_SUFFIXES
    )


def sanitize_string(value: str) -> str:
    sanitized = AUTHORIZATION_HEADER_PATTERN.sub(
        lambda match: f"{match.group(1)} {REDACTED_VALUE}",
        value,
    )
    sanitized = COOKIE_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}={REDACTED_VALUE}",
        sanitized,
    )

    return sanitized


def sanitize_for_logging(
    value: Any,
    *,
    field_name: object | None = None,
) -> Any:
    if field_name is not None and is_sensitive_field(field_name):
        return REDACTED_VALUE

    if isinstance(value, Mapping):
        return {
            key: sanitize_for_logging(
                nested_value,
                field_name=key,
            )
            for key, nested_value in value.items()
        }

    if isinstance(value, list):
        return [sanitize_for_logging(item) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize_for_logging(item) for item in value)

    if isinstance(value, set):
        return {sanitize_for_logging(item) for item in value}

    if isinstance(value, str):
        return sanitize_string(value)

    return value
