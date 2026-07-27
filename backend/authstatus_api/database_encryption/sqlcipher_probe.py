from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class SQLCipherProbeError(RuntimeError):
    pass


def import_sqlcipher() -> Any:
    try:
        import sqlcipher3
    except ImportError as exc:
        raise SQLCipherProbeError(
            "sqlcipher3 is not installed. Run: python -m pip install sqlcipher3"
        ) from exc

    return sqlcipher3


def _sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def apply_sqlcipher_key(conn: Any, passphrase: str) -> None:
    conn.execute(f"PRAGMA key = {_sql_quote(passphrase)}")


def create_sqlcipher_probe_database(
    database_path: Path,
    *,
    passphrase: str,
) -> None:
    if not passphrase:
        raise SQLCipherProbeError("SQLCipher probe passphrase is required.")

    sqlcipher3 = import_sqlcipher()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlcipher3.connect(str(database_path))
    try:
        apply_sqlcipher_key(conn, passphrase)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS probe_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL
            )
            """)
        conn.execute(
            """
            INSERT INTO probe_records (label)
            VALUES (?)
            """,
            ("sqlcipher works",),
        )
        conn.commit()
    finally:
        conn.close()


def read_sqlcipher_probe_database(
    database_path: Path,
    *,
    passphrase: str,
) -> list[str]:
    if not passphrase:
        raise SQLCipherProbeError("SQLCipher probe passphrase is required.")

    sqlcipher3 = import_sqlcipher()

    conn = sqlcipher3.connect(str(database_path))
    try:
        apply_sqlcipher_key(conn, passphrase)
        rows = conn.execute("""
            SELECT label
            FROM probe_records
            ORDER BY id
            """).fetchall()
    finally:
        conn.close()

    return [row[0] for row in rows]


def plaintext_sqlite_can_read_database(database_path: Path) -> bool:
    try:
        conn = sqlite3.connect(database_path)
        try:
            conn.execute("""
                SELECT name
                FROM sqlite_master
                LIMIT 1
                """).fetchall()
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        return False

    return True


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _select_all_query(table_name: str) -> str:
    return " ".join(
        (
            "SELECT",
            "*",
            "FROM",
            _quote_identifier(table_name),
        )
    )


def _insert_rows_query(
    table_name: str,
    column_names: list[str],
) -> str:
    quoted_columns = ", ".join(_quote_identifier(column) for column in column_names)
    placeholders = ", ".join("?" for _ in column_names)

    return " ".join(
        (
            "INSERT",
            "INTO",
            _quote_identifier(table_name),
            f"({quoted_columns})",
            "VALUES",
            f"({placeholders})",
        )
    )


def _table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """).fetchall()

    return [row[0] for row in rows]


def migrate_plaintext_sqlite_to_sqlcipher(
    *,
    source_path: Path,
    destination_path: Path,
    passphrase: str,
) -> Path:
    if not passphrase:
        raise SQLCipherProbeError("SQLCipher migration passphrase is required.")

    if not source_path.exists():
        raise SQLCipherProbeError(f"Source database does not exist: {source_path}")

    if destination_path.exists():
        raise SQLCipherProbeError(f"Destination already exists: {destination_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    sqlcipher3 = import_sqlcipher()

    source_conn = sqlite3.connect(str(source_path))
    destination_conn = sqlcipher3.connect(str(destination_path))

    try:
        source_conn.row_factory = sqlite3.Row
        apply_sqlcipher_key(destination_conn, passphrase)

        schema_rows = source_conn.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE sql IS NOT NULL
              AND type IN ('table', 'index', 'trigger', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY
              CASE type
                WHEN 'table' THEN 1
                WHEN 'index' THEN 2
                WHEN 'trigger' THEN 3
                WHEN 'view' THEN 4
                ELSE 5
              END,
              name
            """).fetchall()

        for row in schema_rows:
            destination_conn.execute(row["sql"])

        for table_name in _table_names(source_conn):
            rows = source_conn.execute(_select_all_query(table_name)).fetchall()

            if not rows:
                continue

            column_names = list(rows[0].keys())

            destination_conn.executemany(
                _insert_rows_query(
                    table_name,
                    column_names,
                ),
                [tuple(row[column] for column in column_names) for row in rows],
            )

        destination_conn.commit()
    except Exception:
        destination_conn.rollback()
        raise
    finally:
        source_conn.close()
        destination_conn.close()

    return destination_path


def verify_sqlcipher_database(
    *,
    database_path: Path,
    passphrase: str,
    required_tables: set[str] | None = None,
) -> dict[str, object]:
    if not passphrase:
        raise SQLCipherProbeError("SQLCipher verification passphrase is required.")

    if not database_path.exists():
        raise SQLCipherProbeError(f"Database does not exist: {database_path}")

    sqlcipher3 = import_sqlcipher()
    expected_tables = required_tables or set()

    conn = sqlcipher3.connect(str(database_path))
    try:
        apply_sqlcipher_key(conn, passphrase)

        rows = conn.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """).fetchall()

        table_names = {row[0] for row in rows}
    finally:
        conn.close()

    missing_tables = sorted(expected_tables - table_names)

    if missing_tables:
        raise SQLCipherProbeError(
            f"SQLCipher database is missing required tables: {missing_tables}"
        )

    return {
        "database_path": str(database_path),
        "tables": sorted(table_names),
        "required_tables": sorted(expected_tables),
        "missing_tables": missing_tables,
    }
