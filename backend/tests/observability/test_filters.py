from __future__ import annotations

import io
import logging

from authstatus_api.observability.filters import (
    SensitiveDataFilter,
)


def formatted_log(
    message: object,
    *,
    args: tuple[object, ...] = (),
    extra: dict[str, object] | None = None,
    exc_info: tuple[type[BaseException], BaseException, object] | None = None,
    format_string: str = "%(message)s",
) -> str:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(SensitiveDataFilter())
    handler.setFormatter(logging.Formatter(format_string))

    logger = logging.getLogger(f"tests.observability.{id(stream)}")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False

    record = logger.makeRecord(
        logger.name,
        logging.ERROR,
        __file__,
        1,
        message,
        args,
        exc_info,
        extra=extra,
    )
    logger.handle(record)

    return stream.getvalue()


def test_filter_redacts_sensitive_extra_fields():
    output = formatted_log(
        "Request failed.",
        extra={
            "session_token": "example-session-token",
        },
        format_string="%(message)s %(session_token)s",
    )

    assert "example-session-token" not in output
    assert output.strip() == "Request failed. [REDACTED]"


def test_filter_redacts_sensitive_mapping_message():
    output = formatted_log(
        {
            "method": "POST",
            "password": "ExamplePassword123!",
            "medical_member_id": "TEST-MEMBER-123",
        }
    )

    assert "ExamplePassword123!" not in output
    assert "TEST-MEMBER-123" not in output
    assert output.count("[REDACTED]") == 2


def test_filter_sanitizes_formatting_arguments():
    output = formatted_log(
        "Request headers: %s",
        args=("Authorization: Bearer example-access-token",),
    )

    assert "example-access-token" not in output
    assert output.strip() == ("Request headers: Authorization: Bearer [REDACTED]")


def test_filter_sanitizes_cookie_values_in_message():
    output = formatted_log("Cookie: carequeue_session=example-session; theme=dark")

    assert "example-session" not in output
    assert output.strip() == ("Cookie: carequeue_session=[REDACTED]; theme=dark")


def test_filter_removes_exception_message_and_traceback():
    try:
        raise ValueError("Patient TEST-MEMBER-123 could not be processed")
    except ValueError as exc:
        output = formatted_log(
            "Unhandled API exception.",
            exc_info=(
                type(exc),
                exc,
                exc.__traceback__,
            ),
            format_string="%(message)s %(exception_type)s",
        )

    assert "TEST-MEMBER-123" not in output
    assert "could not be processed" not in output
    assert "Traceback" not in output
    assert output.strip() == "Unhandled API exception. ValueError"


def test_filter_preserves_non_sensitive_context():
    output = formatted_log(
        "Request completed.",
        extra={
            "method": "POST",
            "path": "/api/auths",
            "status_code": 201,
        },
        format_string=("%(message)s %(method)s %(path)s %(status_code)s"),
    )

    assert output.strip() == ("Request completed. POST /api/auths 201")
