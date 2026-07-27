from __future__ import annotations

import logging

from authstatus_api.observability.filters import SensitiveDataFilter

FILTER_MARKER = "_carequeue_sensitive_data_filter"

MANAGED_LOGGERS = (
    "",
    "authstatus_api",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
)


def _has_sensitive_data_filter(
    handler: logging.Handler,
) -> bool:
    return any(
        getattr(log_filter, FILTER_MARKER, False) for log_filter in handler.filters
    )


def _install_filter(
    handler: logging.Handler,
) -> None:
    if _has_sensitive_data_filter(handler):
        return

    sensitive_filter = SensitiveDataFilter()
    setattr(sensitive_filter, FILTER_MARKER, True)
    handler.addFilter(sensitive_filter)


def configure_application_logging(
    *,
    environment: str,
) -> None:
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())

    for logger_name in MANAGED_LOGGERS:
        logger = logging.getLogger(logger_name)

        for handler in logger.handlers:
            _install_filter(handler)

    if environment == "production":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
