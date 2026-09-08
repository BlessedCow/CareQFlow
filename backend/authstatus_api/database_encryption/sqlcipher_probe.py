from __future__ import annotations

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
