from __future__ import annotations

import pytest
import sqlcipher3

from authstatus_api.database_encryption.sqlcipher_probe import (
    SQLCipherProbeError,
    apply_sqlcipher_key,
    create_sqlcipher_probe_database,
    import_sqlcipher,
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


def test_verify_sqlcipher_database_confirms_required_tables(tmp_path):
    database_path = tmp_path / "database.sqlcipher.db"
    passphrase = "correct horse battery staple"

    sqlcipher3 = import_sqlcipher()
    connection = sqlcipher3.connect(str(database_path))

    try:
        apply_sqlcipher_key(connection, passphrase)

        connection.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL
            )
            """)

        connection.execute("""
            CREATE TABLE auths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL
            )
            """)

        connection.commit()
    finally:
        connection.close()

    result = verify_sqlcipher_database(
        database_path=database_path,
        passphrase=passphrase,
        required_tables={"users", "auths"},
    )

    assert result["database_path"] == str(database_path)
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
