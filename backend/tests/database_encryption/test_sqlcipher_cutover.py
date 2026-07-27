from __future__ import annotations

import sqlite3

import pytest

from authstatus_api.crypto import generate_encryption_key
from authstatus_api.database_encryption.cutover import (
    SQLCipherCutoverError,
    environment_database_path,
    prepare_sqlcipher_cutover,
)
from authstatus_api.database_encryption.sqlcipher_probe import (
    plaintext_sqlite_can_read_database,
    verify_sqlcipher_database,
)
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_BACKUP_ENCRYPTION_KEY", generate_encryption_key())
    monkeypatch.setenv("AUTHSTATUS_BACKUP_DIRECTORY", str(tmp_path / "backups"))
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def create_plaintext_database(database_path):
    conn = sqlite3.connect(str(database_path))
    try:
        conn.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL
            )
            """)
        conn.execute("""
            CREATE TABLE auths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL
            )
            """)
        conn.execute(
            """
            INSERT INTO users (username)
            VALUES (?)
            """,
            ("admin@example.com",),
        )
        conn.execute(
            """
            INSERT INTO auths (client_name)
            VALUES (?)
            """,
            ("Encrypted Test",),
        )
        conn.commit()
    finally:
        conn.close()


def test_environment_database_path_uses_forward_slashes(tmp_path):
    backend_root = tmp_path / "backend"
    database_path = tmp_path / "data" / "auth_tracker.sqlcipher.db"

    assert (
        environment_database_path(database_path, backend_root=backend_root)
        == "../data/auth_tracker.sqlcipher.db"
    )


def test_prepare_sqlcipher_cutover_creates_backup_and_verified_encrypted_database(
    tmp_path,
):
    source_path = tmp_path / "auth_tracker.db"
    destination_path = tmp_path / "auth_tracker.sqlcipher.db"
    backup_directory = tmp_path / "backups"

    create_plaintext_database(source_path)

    result = prepare_sqlcipher_cutover(
        source_path=source_path,
        destination_path=destination_path,
        sqlcipher_key="correct horse battery staple",
        backend_root=tmp_path,
        backup_directory=backup_directory,
        required_tables={"users", "auths"},
    )

    assert result["backup_path"].exists()
    assert result["backup_path"].suffix == ".enc"
    assert result["sqlcipher_path"] == destination_path
    assert destination_path.exists()
    assert plaintext_sqlite_can_read_database(destination_path) is False
    assert result["env_values"] == {
        "AUTHSTATUS_DATABASE_PATH": "auth_tracker.sqlcipher.db",
        "AUTHSTATUS_DATABASE_ENCRYPTION": "sqlcipher",
    }

    verification = verify_sqlcipher_database(
        database_path=destination_path,
        passphrase="correct horse battery staple",
        required_tables={"users", "auths"},
    )

    assert verification["missing_tables"] == []


def test_prepare_sqlcipher_cutover_rejects_existing_destination_without_force(tmp_path):
    source_path = tmp_path / "auth_tracker.db"
    destination_path = tmp_path / "auth_tracker.sqlcipher.db"

    create_plaintext_database(source_path)
    destination_path.write_bytes(b"existing file")

    with pytest.raises(SQLCipherCutoverError):
        prepare_sqlcipher_cutover(
            source_path=source_path,
            destination_path=destination_path,
            sqlcipher_key="correct horse battery staple",
            backend_root=tmp_path,
            required_tables={"users", "auths"},
        )


def test_prepare_sqlcipher_cutover_force_recreates_destination(tmp_path):
    source_path = tmp_path / "auth_tracker.db"
    destination_path = tmp_path / "auth_tracker.sqlcipher.db"

    create_plaintext_database(source_path)
    destination_path.write_bytes(b"existing file")

    result = prepare_sqlcipher_cutover(
        source_path=source_path,
        destination_path=destination_path,
        sqlcipher_key="correct horse battery staple",
        backend_root=tmp_path,
        force=True,
        required_tables={"users", "auths"},
    )

    assert result["sqlcipher_path"] == destination_path
    assert plaintext_sqlite_can_read_database(destination_path) is False


def test_prepare_sqlcipher_cutover_requires_sqlcipher_key(tmp_path):
    source_path = tmp_path / "auth_tracker.db"
    create_plaintext_database(source_path)

    with pytest.raises(SQLCipherCutoverError):
        prepare_sqlcipher_cutover(
            source_path=source_path,
            destination_path=None,
            sqlcipher_key="",
            backend_root=tmp_path,
            required_tables={"users", "auths"},
        )
