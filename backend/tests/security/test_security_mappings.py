from __future__ import annotations

from datetime import UTC, datetime

from authstatus_api.security.mappings import (
    format_datetime,
    parse_datetime,
    session_row_to_dict,
    user_row_to_dict,
)


def test_format_datetime_normalizes_to_utc():
    value = datetime(
        2026,
        7,
        20,
        12,
        30,
        45,
        tzinfo=UTC,
    )

    assert format_datetime(value) == ("2026-07-20T12:30:45+00:00")


def test_parse_datetime_returns_utc_datetime():
    value = parse_datetime("2026-07-20T12:30:45+00:00")

    assert value == datetime(
        2026,
        7,
        20,
        12,
        30,
        45,
        tzinfo=UTC,
    )


def test_user_row_to_dict_converts_boolean_fields():
    user = user_row_to_dict(
        {
            "id": 1,
            "username": "reviewer",
            "is_active": 1,
            "must_change_password": 0,
            "mfa_enabled": 1,
        }
    )

    assert user == {
        "id": 1,
        "username": "reviewer",
        "is_active": True,
        "must_change_password": False,
        "mfa_enabled": True,
    }


def test_user_row_to_dict_handles_none():
    assert user_row_to_dict(None) is None


def test_session_row_to_dict_returns_mapping():
    session = session_row_to_dict(
        {
            "id": 1,
            "user_id": 2,
        }
    )

    assert session == {
        "id": 1,
        "user_id": 2,
    }


def test_session_row_to_dict_handles_none():
    assert session_row_to_dict(None) is None
