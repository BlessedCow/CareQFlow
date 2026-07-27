from __future__ import annotations

import io
import logging

from fastapi.testclient import TestClient

from authstatus_api.errors import SAFE_INTERNAL_ERROR_MESSAGE
from authstatus_api.main import create_app


def test_unhandled_exception_does_not_log_sensitive_message():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        logging.Formatter("%(message)s %(method)s %(path)s %(exception_type)s")
    )

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        api = create_app()

        @api.get("/api/test/unhandled-exception")
        def raise_unhandled_exception() -> None:
            raise ValueError(
                "Patient TEST-MEMBER-123 with DOB 01/02/1990 " "could not be processed"
            )

        with TestClient(
            api,
            raise_server_exceptions=False,
        ) as client:
            client.cookies.set(
                "carequeue_session",
                "example-session-token",
            )
            response = client.get(
                "/api/test/unhandled-exception",
            )

        output = stream.getvalue()
    finally:
        root_logger.removeHandler(handler)
        handler.close()

    assert response.status_code == 500
    assert response.json() == {
        "detail": SAFE_INTERNAL_ERROR_MESSAGE,
    }

    assert "TEST-MEMBER-123" not in output
    assert "01/02/1990" not in output
    assert "example-session-token" not in output
    assert "could not be processed" not in output
    assert "Traceback" not in output

    assert (
        "Unhandled API exception. " "GET /api/test/unhandled-exception ValueError"
    ) in output
