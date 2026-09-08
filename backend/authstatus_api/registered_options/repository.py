from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from sqlcipher3 import IntegrityError

from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.schema import init_db

RegisteredOptionCategory = Literal[
    "facility",
    "insurance",
    "web_portal",
]

REGISTERED_OPTION_CATEGORIES = {
    "facility",
    "insurance",
    "web_portal",
}


class RegisteredOptionAlreadyExistsError(ValueError):
    pass


class ProtectedRegisteredOptionError(ValueError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _normalize_display_name(name: str) -> str:
    normalized_name = " ".join(name.split())

    if not normalized_name:
        raise ValueError("Option name is required.")

    return normalized_name


def _normalize_lookup_name(name: str) -> str:
    return _normalize_display_name(name).casefold()


def _validate_category(category: str) -> RegisteredOptionCategory:
    if category not in REGISTERED_OPTION_CATEGORIES:
        raise ValueError("Invalid registered option category.")

    return category  # type: ignore[return-value]


def _row_to_option(row: Any) -> dict[str, Any] | None:
    if row is None:
        return None

    option = dict(row)
    option["is_protected"] = bool(option["is_protected"])

    return option


def list_registered_options(
    *,
    category: str | None = None,
) -> list[dict[str, Any]]:
    init_db()

    if category is None:
        query = """
            SELECT *
            FROM registered_options
            ORDER BY category, normalized_name
        """
        values: tuple[Any, ...] = ()
    else:
        validated_category = _validate_category(category)
        query = """
            SELECT *
            FROM registered_options
            WHERE category = ?
            ORDER BY normalized_name
        """
        values = (validated_category,)

    with get_conn() as conn:
        rows = conn.execute(query, values).fetchall()

    return [option for row in rows if (option := _row_to_option(row)) is not None]


def get_registered_option(
    option_id: int,
) -> dict[str, Any] | None:
    init_db()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM registered_options
            WHERE id = ?
            """,
            (option_id,),
        ).fetchone()

    return _row_to_option(row)


def create_registered_option(
    *,
    category: str,
    name: str,
) -> dict[str, Any]:
    init_db()

    validated_category = _validate_category(category)
    display_name = _normalize_display_name(name)
    normalized_name = _normalize_lookup_name(name)
    now = _now()

    try:
        with get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO registered_options (
                    category,
                    name,
                    normalized_name,
                    is_protected,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 0, ?, ?)
                """,
                (
                    validated_category,
                    display_name,
                    normalized_name,
                    now,
                    now,
                ),
            )

            option_id = int(cursor.lastrowid)
    except IntegrityError as error:
        raise RegisteredOptionAlreadyExistsError(
            "A registered option with this name already exists."
        ) from error

    option = get_registered_option(option_id)

    if option is None:
        raise RuntimeError("Unable to create registered option.")

    return option


def delete_registered_option(option_id: int) -> bool:
    init_db()

    option = get_registered_option(option_id)

    if option is None:
        return False

    if option["is_protected"]:
        raise ProtectedRegisteredOptionError(
            "Protected registered options cannot be deleted."
        )

    with get_conn() as conn:
        cursor = conn.execute(
            """
            DELETE FROM registered_options
            WHERE id = ?
            """,
            (option_id,),
        )

    return cursor.rowcount > 0
