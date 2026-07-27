from __future__ import annotations

import sqlite3

import pytest
import sqlcipher3

from authstatus_api.database_encryption.sqlcipher_probe import (
    SQLCipherProbeError,
    _insert_rows_query,
    _select_all_query,
    apply_sqlcipher_key,
    create_sqlcipher_probe_database,
    import_sqlcipher,
    migrate_plaintext_sqlite_to_sqlcipher,
    plaintext_sqlite_can_read_database,
    read_sqlcipher_probe_database,
    verify_sqlcipher_database,
)


def test_sqlcipher_dependency_is_available():
    try:
        sqlcipher3 = import_sqlcipher()
    except SQLCipherProbeError as exc:
        pytest.fail(str(exc))

    assert sqlcipher3 is not None


def test_sqlcipher_can_write_and_read_encrypted_database(tmp_path):
    database_path = tmp_path / "probe_encrypted.db"

    create_sqlcipher_probe_database(
        database_path,
        passphrase="correct horse battery staple",
    )

    records = read_sqlcipher_probe_database(
        database_path,
        passphrase="correct horse battery staple",
    )

    assert records == ["sqlcipher works"]


def test_plaintext_sqlite_cannot_read_sqlcipher_database(tmp_path):
    database_path = tmp_path / "probe_encrypted.db"

    create_sqlcipher_probe_database(
        database_path,
        passphrase="correct horse battery staple",
    )

    assert plaintext_sqlite_can_read_database(database_path) is False


def test_sqlcipher_rejects_wrong_passphrase(tmp_path):
    database_path = tmp_path / "probe_encrypted.db"

    create_sqlcipher_probe_database(
        database_path,
        passphrase="correct horse battery staple",
    )

    with pytest.raises(sqlcipher3.DatabaseError):
        read_sqlcipher_probe_database(
            database_path,
            passphrase="wrong passphrase",
        )


def test_migrate_plaintext_sqlite_to_sqlcipher_copies_schema_and_data(tmp_path):
    source_path = tmp_path / "source.db"
    destination_path = tmp_path / "destination.sqlcipher.db"

    plaintext_conn = sqlite3.connect(str(source_path))
    try:
        plaintext_conn.execute("""
            CREATE TABLE records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
            """)
        plaintext_conn.execute(
            """
            INSERT INTO records (name)
            VALUES (?)
            """,
            ("test record",),
        )
        plaintext_conn.commit()
    finally:
        plaintext_conn.close()

    migrated_path = migrate_plaintext_sqlite_to_sqlcipher(
        source_path=source_path,
        destination_path=destination_path,
        passphrase="correct horse battery staple",
    )

    assert migrated_path == destination_path
    assert destination_path.exists()
    assert plaintext_sqlite_can_read_database(destination_path) is False

    sqlcipher3 = import_sqlcipher()
    encrypted_conn = sqlcipher3.connect(str(destination_path))
    try:
        apply_sqlcipher_key(encrypted_conn, "correct horse battery staple")
        rows = encrypted_conn.execute("""
            SELECT name
            FROM records
            """).fetchall()
    finally:
        encrypted_conn.close()

    assert [row[0] for row in rows] == ["test record"]


def test_verify_sqlcipher_database_confirms_required_tables(tmp_path):
    source_path = tmp_path / "source.db"
    destination_path = tmp_path / "destination.sqlcipher.db"

    plaintext_conn = sqlite3.connect(str(source_path))
    try:
        plaintext_conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL
            )
            """)
        plaintext_conn.execute("""
            CREATE TABLE auths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL
            )
            """)
        plaintext_conn.commit()
    finally:
        plaintext_conn.close()

    migrate_plaintext_sqlite_to_sqlcipher(
        source_path=source_path,
        destination_path=destination_path,
        passphrase="correct horse battery staple",
    )

    result = verify_sqlcipher_database(
        database_path=destination_path,
        passphrase="correct horse battery staple",
        required_tables={"users", "auths"},
    )

    assert result["database_path"] == str(destination_path)
    assert result["required_tables"] == ["auths", "users"]
    assert result["missing_tables"] == []
    assert "users" in result["tables"]
    assert "auths" in result["tables"]


def test_verify_sqlcipher_database_rejects_missing_required_table(tmp_path):
    database_path = tmp_path / "probe_encrypted.db"

    create_sqlcipher_probe_database(
        database_path,
        passphrase="correct horse battery staple",
    )

    with pytest.raises(SQLCipherProbeError):
        verify_sqlcipher_database(
            database_path=database_path,
            passphrase="correct horse battery staple",
            required_tables={"missing_table"},
        )


def test_select_all_query_quotes_table_name():
    query = _select_all_query('records"archive')

    assert query == 'SELECT * FROM "records""archive"'


def test_insert_rows_query_quotes_identifiers():
    query = _insert_rows_query(
        'records"archive',
        ["id", 'display"name'],
    )

    assert query == (
        'INSERT INTO "records""archive" ' '("id", "display""name") VALUES (?, ?)'
    )
