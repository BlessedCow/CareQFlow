from authstatus_api.observability.sanitization import (
    REDACTED_VALUE,
    is_sensitive_field,
    sanitize_for_logging,
    sanitize_string,
)


def test_sensitive_field_names_are_detected():
    assert is_sensitive_field("password") is True
    assert is_sensitive_field("session-token") is True
    assert is_sensitive_field("medical_member_id") is True
    assert is_sensitive_field("date_of_birth") is True
    assert is_sensitive_field("display_name") is False


def test_sensitive_mapping_values_are_redacted():
    sanitized = sanitize_for_logging(
        {
            "username": "test.user@example.invalid",
            "password": "ExamplePassword123!",
            "session_token": "example-session-token",
            "medical_member_id": "TEST-MEMBER-123",
            "medical_group_number": "TEST-GROUP-456",
            "date_of_birth": "01/02/1990",
        }
    )

    assert sanitized == {
        "username": "test.user@example.invalid",
        "password": REDACTED_VALUE,
        "session_token": REDACTED_VALUE,
        "medical_member_id": REDACTED_VALUE,
        "medical_group_number": REDACTED_VALUE,
        "date_of_birth": REDACTED_VALUE,
    }


def test_nested_sensitive_values_are_redacted():
    sanitized = sanitize_for_logging(
        {
            "request": {
                "headers": {
                    "authorization": "Bearer example-token",
                    "content_type": "application/json",
                },
                "body": {
                    "patient": {
                        "member_id": "TEST-MEMBER-123",
                    }
                },
            }
        }
    )

    assert sanitized == {
        "request": {
            "headers": {
                "authorization": REDACTED_VALUE,
                "content_type": "application/json",
            },
            "body": {
                "patient": {
                    "member_id": REDACTED_VALUE,
                }
            },
        }
    }


def test_authorization_header_is_redacted_inside_string():
    message = sanitize_string(
        "Request failed with Authorization: Bearer example-token-value"
    )

    assert message == ("Request failed with Authorization: Bearer [REDACTED]")


def test_session_cookie_is_redacted_inside_string():
    message = sanitize_string("Cookie: carequeue_session=example-session; theme=dark")

    assert message == ("Cookie: carequeue_session=[REDACTED]; theme=dark")


def test_non_sensitive_values_are_preserved():
    sanitized = sanitize_for_logging(
        {
            "method": "POST",
            "path": "/api/auths",
            "status_code": 422,
            "tags": ["validation", "request"],
        }
    )

    assert sanitized == {
        "method": "POST",
        "path": "/api/auths",
        "status_code": 422,
        "tags": ["validation", "request"],
    }
