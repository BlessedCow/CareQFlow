from __future__ import annotations

import sqlite3

import pytest

from authstatus_api.backups.service import (
    BackupConfigError,
    BackupError,
    create_encrypted_database_backup,
    decrypt_backup_file,
    encrypt_backup_bytes,
    restore_encrypted_database_backup,
)
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.persistence.schema import init_db
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_test_settings(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_PATH",
        str(tmp_path / "auth_tracker.db"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_DIRECTORY",
        str(tmp_path / "backups"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_RESTORE_DIRECTORY",
        str(tmp_path / "restores"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    monkeypatch.setenv("AUTHSTATUS_DATABASE_ENCRYPTION", "plaintext")
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def test_encrypt_backup_bytes_does_not_return_plaintext():
    plaintext = b"SQLite format 3\x00test database bytes"

    encrypted = encrypt_backup_bytes(plaintext)

    assert encrypted != plaintext
    assert b"SQLite format 3" not in encrypted


def test_create_encrypted_database_backup_writes_encrypted_snapshot(tmp_path):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"

    init_db()

    with sqlite3.connect(database_path) as conn:
        conn.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                is_active,
                failed_login_count,
                password_changed_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "backup@example.com",
                "test-password-hash",
                "Admin",
                1,
                0,
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
            ),
        )

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    assert backup_path.exists()
    assert backup_path.name.startswith("auth_tracker_")
    assert backup_path.name.endswith(".db.enc")
    assert b"backup@example.com" not in backup_path.read_bytes()

    decrypted_snapshot = decrypt_backup_file(backup_path)
    restored_snapshot_path = tmp_path / "snapshot.db"
    restored_snapshot_path.write_bytes(decrypted_snapshot)

    with sqlite3.connect(restored_snapshot_path) as conn:
        username = conn.execute(
            "SELECT username FROM users WHERE username = ?",
            ("backup@example.com",),
        ).fetchone()

        integrity_result = conn.execute("PRAGMA quick_check").fetchone()

    assert username is not None
    assert username[0] == "backup@example.com"
    assert integrity_result is not None
    assert integrity_result[0] == "ok"


def test_create_encrypted_database_backup_removes_temporary_snapshot(
    tmp_path,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"

    init_db()

    create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    assert not list(backup_directory.glob(".*.snapshot.*"))
    assert not list(backup_directory.glob("*.tmp"))


def test_create_encrypted_database_backup_rejects_invalid_plaintext_database(
    tmp_path,
):
    database_path = tmp_path / "invalid.db"
    backup_directory = tmp_path / "backups"

    database_path.write_bytes(b"not a valid SQLite database")

    with pytest.raises(
        BackupError,
        match="consistent plaintext database snapshot",
    ):
        create_encrypted_database_backup(
            database_path=database_path,
            backup_directory=backup_directory,
        )

    assert not list(backup_directory.glob("*.db.enc"))
    assert not list(backup_directory.glob(".*.snapshot.*"))


def test_create_encrypted_database_backup_rejects_missing_database(tmp_path):
    missing_database_path = tmp_path / "missing.db"

    with pytest.raises(BackupError):
        create_encrypted_database_backup(database_path=missing_database_path)


def test_encrypt_backup_bytes_requires_backup_key(monkeypatch):
    monkeypatch.setenv("AUTHSTATUS_BACKUP_ENCRYPTION_KEY", "")
    get_settings.cache_clear()

    with pytest.raises(BackupConfigError):
        encrypt_backup_bytes(b"database bytes")


def test_restore_encrypted_database_backup_writes_valid_safe_restore_file(
    tmp_path,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    init_db()

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    restored_path = restore_encrypted_database_backup(
        backup_path=backup_path,
        restore_directory=restore_directory,
    )

    assert restored_path.exists()
    assert restored_path.parent == restore_directory
    assert restored_path.name.endswith(".restored.db")

    with sqlite3.connect(database_path) as original_conn:
        original_tables = {row[0] for row in original_conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """).fetchall()}

    with sqlite3.connect(restored_path) as restored_conn:
        restored_tables = {row[0] for row in restored_conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """).fetchall()}

        integrity_result = restored_conn.execute("PRAGMA quick_check").fetchone()

    assert restored_tables == original_tables
    assert integrity_result is not None
    assert integrity_result[0] == "ok"


def test_restore_rejects_decrypted_file_that_is_not_a_carequeue_database(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"
    backup_directory.mkdir(parents=True)

    backup_path = backup_directory / "invalid.db.enc"
    backup_path.write_bytes(encrypt_backup_bytes(b"not a CareQueue database"))

    with pytest.raises(
        BackupError,
        match="not a valid plaintext SQLite database",
    ):
        restore_encrypted_database_backup(
            backup_path=backup_path,
            restore_directory=restore_directory,
        )

    assert not list(restore_directory.glob("*.restored.db"))
    assert not list(restore_directory.glob("*.tmp"))
