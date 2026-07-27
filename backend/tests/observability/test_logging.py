from __future__ import annotations

import logging

from authstatus_api.observability.filters import (
    SensitiveDataFilter,
)
from authstatus_api.observability.logging import (
    configure_application_logging,
)


def sensitive_filter_count(
    handler: logging.Handler,
) -> int:
    return sum(
        isinstance(log_filter, SensitiveDataFilter) for log_filter in handler.filters
    )


def test_configure_logging_adds_root_handler_when_missing(
    monkeypatch,
):
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)

    monkeypatch.setattr(root_logger, "handlers", [])

    configure_application_logging(
        environment="development",
    )

    assert len(root_logger.handlers) == 1
    assert sensitive_filter_count(root_logger.handlers[0]) == 1

    root_logger.handlers = original_handlers


def test_configure_logging_filters_existing_handlers(
    monkeypatch,
):
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()

    monkeypatch.setattr(
        root_logger,
        "handlers",
        [handler],
    )

    configure_application_logging(
        environment="development",
    )

    assert sensitive_filter_count(handler) == 1


def test_configure_logging_is_idempotent(
    monkeypatch,
):
    root_logger = logging.getLogger()
    handler = logging.StreamHandler()

    monkeypatch.setattr(
        root_logger,
        "handlers",
        [handler],
    )

    configure_application_logging(
        environment="development",
    )
    configure_application_logging(
        environment="development",
    )

    assert sensitive_filter_count(handler) == 1


def test_production_reduces_access_log_level(
    monkeypatch,
):
    access_logger = logging.getLogger("uvicorn.access")
    original_level = access_logger.level

    monkeypatch.setattr(
        logging.getLogger(),
        "handlers",
        [logging.StreamHandler()],
    )

    configure_application_logging(
        environment="production",
    )

    assert access_logger.level == logging.WARNING

    access_logger.setLevel(original_level)


def test_development_preserves_access_log_level(
    monkeypatch,
):
    access_logger = logging.getLogger("uvicorn.access")
    original_level = access_logger.level
    access_logger.setLevel(logging.INFO)

    monkeypatch.setattr(
        logging.getLogger(),
        "handlers",
        [logging.StreamHandler()],
    )

    configure_application_logging(
        environment="development",
    )

    assert access_logger.level == logging.INFO

    access_logger.setLevel(original_level)
