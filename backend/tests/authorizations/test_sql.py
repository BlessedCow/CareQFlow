from __future__ import annotations

import pytest

from authstatus_api.authorizations.sql import (
    insert_sql,
    sql_columns,
    update_assignments,
)


def test_sql_columns_preserves_payload_order():
    columns = sql_columns(
        {
            "status": "Pending",
            "unknown": "ignored",
            "client_name": "Example Patient",
            "id": 1,
        },
        {
            "id",
            "status",
            "client_name",
        },
        {"id"},
    )

    assert columns == [
        "status",
        "client_name",
    ]


def test_sql_columns_handles_empty_payload():
    assert (
        sql_columns(
            {},
            {"status"},
            set(),
        )
        == []
    )


def test_insert_sql_builds_statement():
    statement = insert_sql(
        "auths",
        [
            "client_name",
            "status",
        ],
    )

    assert statement == ("INSERT INTO auths " "(client_name, status) VALUES (?, ?)")


def test_update_assignments_builds_statement():
    assignments = update_assignments(
        [
            "status",
            "updated_at",
        ]
    )

    assert assignments == ("status = ?, updated_at = ?")


@pytest.mark.parametrize(
    "identifier",
    [
        "auths; DROP TABLE users",
        "auths --",
        "auths records",
        "auths.table",
        "1auths",
        "",
    ],
)
def test_insert_sql_rejects_invalid_table_names(
    identifier: str,
):
    with pytest.raises(
        ValueError,
        match="Invalid SQL identifier",
    ):
        insert_sql(identifier, ["client_name"])


@pytest.mark.parametrize(
    "identifier",
    [
        "client_name = 'changed'",
        "client-name",
        "client name",
        "client_name;",
        "auths.client_name",
        "",
    ],
)
def test_insert_sql_rejects_invalid_column_names(
    identifier: str,
):
    with pytest.raises(
        ValueError,
        match="Invalid SQL identifier",
    ):
        insert_sql("auths", [identifier])


def test_update_assignments_rejects_invalid_columns():
    with pytest.raises(
        ValueError,
        match="Invalid SQL identifier",
    ):
        update_assignments(["client_name; DROP TABLE auths"])
