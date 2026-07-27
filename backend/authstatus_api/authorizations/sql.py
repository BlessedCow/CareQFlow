from __future__ import annotations

import re
from typing import Any

SQL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(identifier: str) -> str:
    if not SQL_IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")

    return identifier


def sql_columns(
    payload: dict[str, Any],
    allowed_columns: set[str],
    excluded_columns: set[str],
) -> list[str]:
    return [
        key for key in payload if key in allowed_columns and key not in excluded_columns
    ]


def insert_sql(
    table_name: str,
    columns: list[str],
) -> str:
    validated_table_name = _validate_identifier(table_name)
    validated_columns = [_validate_identifier(column) for column in columns]

    column_names = ", ".join(validated_columns)
    placeholders = ", ".join("?" for _ in validated_columns)

    return " ".join(
        (
            "INSERT",
            "INTO",
            validated_table_name,
            f"({column_names})",
            "VALUES",
            f"({placeholders})",
        )
    )


def update_assignments(columns: list[str]) -> str:
    validated_columns = [_validate_identifier(column) for column in columns]

    return ", ".join(f"{column} = ?" for column in validated_columns)
