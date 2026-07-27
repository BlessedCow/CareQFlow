from __future__ import annotations

import logging
from typing import Any

from authstatus_api.observability.sanitization import (
    sanitize_for_logging,
    sanitize_string,
)

STANDARD_LOG_RECORD_FIELDS = frozenset(logging.makeLogRecord({}).__dict__)


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._sanitize_message(record.msg)
        record.args = self._sanitize_arguments(record.args)

        for field_name, value in tuple(record.__dict__.items()):
            if field_name in STANDARD_LOG_RECORD_FIELDS:
                continue

            record.__dict__[field_name] = sanitize_for_logging(
                value,
                field_name=field_name,
            )

        self._remove_exception_details(record)
        return True

    @staticmethod
    def _sanitize_message(message: object) -> object:
        if isinstance(message, str):
            return sanitize_string(message)

        return sanitize_for_logging(message)

    @staticmethod
    def _sanitize_arguments(arguments: Any) -> Any:
        if isinstance(arguments, dict):
            return sanitize_for_logging(arguments)

        if isinstance(arguments, tuple):
            return tuple(sanitize_for_logging(argument) for argument in arguments)

        return sanitize_for_logging(arguments)

    @staticmethod
    def _remove_exception_details(
        record: logging.LogRecord,
    ) -> None:
        if record.exc_info is None:
            return

        exception_type = record.exc_info[0]

        if exception_type is not None:
            record.__dict__.setdefault(
                "exception_type",
                exception_type.__name__,
            )

        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
