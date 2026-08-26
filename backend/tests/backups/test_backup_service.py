from __future__ import annotations

import json
import os
import sqlite3

import pytest

import authstatus_api.backups.service as backup_service
from authstatus_api.backups.service import (
    PENDING_RECOVERY_MANIFEST,
    BackupConfigError,
    BackupError,
    cancel_staged_database_recovery,
    create_encrypted_database_backup,
    decrypt_backup_file,
    encrypt_backup_bytes,
    get_staged_database_recovery,
    list_encrypted_database_backups,
    resolve_encrypted_database_backup_path,
    restore_encrypted_database_backup,
    stage_encrypted_database_recovery,
    verify_encrypted_database_backup,
)
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.persistence.schema import init_db
from authstatus_api.settings import get_settings


def test_verify_encrypted_database_backup_accepts_valid_backup(
    tmp_path,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"

    init_db()

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    verify_encrypted_database_backup(backup_path=backup_path)

    assert backup_path.exists()
    assert not list(backup_directory.glob(".*.verify.*"))


def test_verify_encrypted_database_backup_rejects_wrong_key(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"

    init_db()

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_ENCRYPTION_KEY",
        generate_encryption_key(),
    )
    get_settings.cache_clear()

    with pytest.raises(
        BackupError,
        match="Unable to decrypt backup file",
    ):
        verify_encrypted_database_backup(backup_path=backup_path)

    assert backup_path.exists()
    assert not list(backup_directory.glob(".*.verify.*"))


def test_verify_encrypted_database_backup_rejects_corrupted_backup(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    backup_path = backup_directory / "corrupted.db.enc"
    backup_path.write_bytes(b"not an encrypted CareQueue backup")

    with pytest.raises(
        BackupError,
        match="Unable to decrypt backup file",
    ):
        verify_encrypted_database_backup(backup_path=backup_path)

    assert not list(backup_directory.glob(".*.verify.*"))


def test_verify_encrypted_database_backup_rejects_empty_backup(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    backup_path = backup_directory / "empty.db.enc"
    backup_path.touch()

    with pytest.raises(
        BackupError,
        match="Backup file is empty",
    ):
        verify_encrypted_database_backup(backup_path=backup_path)

    assert not list(backup_directory.glob(".*.verify.*"))


def test_verify_encrypted_database_backup_removes_invalid_decrypted_file(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    backup_path = backup_directory / "invalid-database.db.enc"
    backup_path.write_bytes(encrypt_backup_bytes(b"not a CareQueue database"))

    with pytest.raises(
        BackupError,
        match="not a valid plaintext SQLite database",
    ):
        verify_encrypted_database_backup(backup_path=backup_path)

    assert backup_path.exists()
    assert not list(backup_directory.glob(".*.verify.*"))


@pytest.mark.parametrize(
    "filename",
    [
        "../auth_tracker_20260729_120000_000001.db.enc",
        r"..\auth_tracker_20260729_120000_000001.db.enc",
        "/tmp/auth_tracker_20260729_120000_000001.db.enc",
        ".auth_tracker_20260729_120000_000001.db.enc",
        "backup.sqlite",
        "backup.enc",
        "backup.db",
        "backup file.db.enc",
        "backup\nfile.db.enc",
    ],
)
def test_resolve_encrypted_backup_rejects_untrusted_filename(
    filename,
):
    with pytest.raises(
        BackupError,
        match="Invalid backup filename",
    ):
        resolve_encrypted_database_backup_path(
            filename=filename,
        )


def test_verify_encrypted_backup_rejects_path_with_nested_component(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    nested_directory = backup_directory / "nested"
    nested_directory.mkdir(parents=True)

    backup_path = nested_directory / "auth_tracker_20260729_120000_000001.db.enc"
    backup_path.write_bytes(b"encrypted data")

    with pytest.raises(
        BackupError,
        match="Unable to decrypt backup file",
    ):
        verify_encrypted_database_backup(
            backup_path=backup_path,
        )


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


def test_create_encrypted_database_backup_reports_directory_creation_failure(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"

    init_db()

    original_mkdir = backup_service.Path.mkdir

    def fail_backup_directory_mkdir(
        path,
        *args,
        **kwargs,
    ):
        if path == backup_directory:
            raise PermissionError("permission denied")

        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(
        backup_service.Path,
        "mkdir",
        fail_backup_directory_mkdir,
    )

    with pytest.raises(
        BackupError,
        match="Unable to create backup directory",
    ):
        create_encrypted_database_backup(
            database_path=database_path,
            backup_directory=backup_directory,
        )

    assert not backup_directory.exists()


def test_create_encrypted_database_backup_reports_atomic_write_failure(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"

    init_db()

    def fail_fsync(_fd):
        raise OSError("disk full")

    monkeypatch.setattr(
        backup_service.os,
        "fsync",
        fail_fsync,
    )

    with pytest.raises(
        BackupError,
        match="Unable to write encrypted backup",
    ):
        create_encrypted_database_backup(
            database_path=database_path,
            backup_directory=backup_directory,
        )

    assert not list(backup_directory.glob("*.db.enc"))


def test_failed_backup_write_removes_partial_and_snapshot_files(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"

    init_db()

    def fail_fsync(_fd):
        raise OSError("disk full")

    monkeypatch.setattr(
        backup_service.os,
        "fsync",
        fail_fsync,
    )

    with pytest.raises(BackupError):
        create_encrypted_database_backup(
            database_path=database_path,
            backup_directory=backup_directory,
        )

    assert not list(backup_directory.glob("*.db.enc"))
    assert not list(backup_directory.glob(".*.snapshot.*"))
    assert not list(backup_directory.glob("*.tmp"))
    assert not list(backup_directory.glob(".*.tmp"))


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


def test_restore_encrypted_database_backup_reports_directory_creation_failure(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    init_db()

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    original_mkdir = backup_service.Path.mkdir

    def fail_restore_directory_mkdir(
        path,
        *args,
        **kwargs,
    ):
        if path == restore_directory:
            raise PermissionError("permission denied")

        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(
        backup_service.Path,
        "mkdir",
        fail_restore_directory_mkdir,
    )

    with pytest.raises(
        BackupError,
        match="Unable to create restore directory",
    ):
        restore_encrypted_database_backup(
            backup_path=backup_path,
            restore_directory=restore_directory,
        )

    assert not restore_directory.exists()


def test_restore_encrypted_database_backup_reports_atomic_write_failure(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    init_db()

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    def fail_fsync(_fd):
        raise OSError("disk full")

    monkeypatch.setattr(
        backup_service.os,
        "fsync",
        fail_fsync,
    )

    with pytest.raises(
        BackupError,
        match="Unable to write restored database",
    ):
        restore_encrypted_database_backup(
            backup_path=backup_path,
            restore_directory=restore_directory,
        )

    assert not list(restore_directory.glob("*.restored.db"))
    assert not list(restore_directory.glob("*.tmp"))
    assert not list(restore_directory.glob(".*.tmp"))


def test_stage_recovery_manifest_write_failure_removes_staged_database(
    tmp_path,
    monkeypatch,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    init_db()

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    original_atomic_write = backup_service._atomic_write_bytes

    def fail_manifest_write(destination_path, data):
        if destination_path.name == PENDING_RECOVERY_MANIFEST:
            raise BackupError("manifest write failed")

        return original_atomic_write(destination_path, data)

    monkeypatch.setattr(
        backup_service,
        "_atomic_write_bytes",
        fail_manifest_write,
    )

    with pytest.raises(
        BackupError,
        match="manifest write failed",
    ):
        stage_encrypted_database_recovery(
            filename=backup_path.name,
            backup_directory=backup_directory,
            restore_directory=restore_directory,
        )

    assert not (restore_directory / PENDING_RECOVERY_MANIFEST).exists()
    assert not list(restore_directory.glob("*.restored.db"))
    assert not list(restore_directory.glob("*.tmp"))
    assert not list(restore_directory.glob(".*.tmp"))


def test_list_encrypted_database_backups_returns_newest_first(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    older_backup = backup_directory / "auth_tracker_older.db.enc"
    newer_backup = backup_directory / "auth_tracker_newer.db.enc"

    older_backup.write_bytes(b"older encrypted backup")
    newer_backup.write_bytes(b"newer encrypted backup")

    os.utime(
        older_backup,
        (1_700_000_000, 1_700_000_000),
    )
    os.utime(
        newer_backup,
        (1_800_000_000, 1_800_000_000),
    )

    backups = list_encrypted_database_backups(
        backup_directory=backup_directory,
    )

    assert [backup["filename"] for backup in backups] == [
        "auth_tracker_newer.db.enc",
        "auth_tracker_older.db.enc",
    ]
    assert backups[0]["size_bytes"] == len(b"newer encrypted backup")
    assert backups[0]["created_at"] == "2027-01-15T08:00:00+00:00"


def test_list_encrypted_database_backups_ignores_unrelated_files(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    valid_backup = backup_directory / "auth_tracker_valid.db.enc"
    valid_backup.write_bytes(b"encrypted backup")

    (backup_directory / "notes.txt").write_text(
        "not a backup",
        encoding="utf-8",
    )
    (backup_directory / "database.db").write_bytes(b"unencrypted database")
    (backup_directory / ".temporary.db.enc").write_bytes(b"temporary backup")

    nested_directory = backup_directory / "nested.db.enc"
    nested_directory.mkdir()

    backups = list_encrypted_database_backups(
        backup_directory=backup_directory,
    )

    assert backups == [
        {
            "filename": "auth_tracker_valid.db.enc",
            "size_bytes": len(b"encrypted backup"),
            "created_at": backups[0]["created_at"],
        }
    ]


def test_list_encrypted_database_backups_returns_empty_for_missing_directory(
    tmp_path,
):
    backups = list_encrypted_database_backups(
        backup_directory=tmp_path / "missing-backups",
    )

    assert backups == []


def test_list_encrypted_database_backups_rejects_file_as_directory(
    tmp_path,
):
    invalid_directory = tmp_path / "backups"
    invalid_directory.write_text(
        "not a directory",
        encoding="utf-8",
    )

    with pytest.raises(
        BackupError,
        match="Backup directory path is not a directory",
    ):
        list_encrypted_database_backups(
            backup_directory=invalid_directory,
        )


def test_resolve_encrypted_database_backup_path_accepts_listed_backup(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    backup_path = backup_directory / "auth_tracker_valid.db.enc"
    backup_path.write_bytes(b"encrypted backup")

    resolved_path = resolve_encrypted_database_backup_path(
        filename=backup_path.name,
        backup_directory=backup_directory,
    )

    assert resolved_path == backup_path.resolve()


@pytest.mark.parametrize(
    "filename",
    [
        "",
        ".",
        "..",
        "../outside.db.enc",
        "..\\outside.db.enc",
        "nested/backup.db.enc",
        "nested\\backup.db.enc",
        "/absolute/backup.db.enc",
        "C:\\absolute\\backup.db.enc",
        ".temporary.db.enc",
        "backup.db",
        "backup.enc",
        "backup.db.enc\x00extra",
    ],
)
def test_resolve_encrypted_database_backup_path_rejects_unsafe_filename(
    tmp_path,
    filename,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    with pytest.raises(
        BackupError,
        match="Invalid backup filename",
    ):
        resolve_encrypted_database_backup_path(
            filename=filename,
            backup_directory=backup_directory,
        )


def test_resolve_encrypted_database_backup_path_rejects_missing_backup(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    with pytest.raises(
        BackupError,
        match="Backup file does not exist",
    ):
        resolve_encrypted_database_backup_path(
            filename="missing.db.enc",
            backup_directory=backup_directory,
        )


def test_resolve_encrypted_database_backup_path_rejects_directory(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    nested_directory = backup_directory / "nested.db.enc"
    nested_directory.mkdir()

    with pytest.raises(
        BackupError,
        match="Backup path is not a file",
    ):
        resolve_encrypted_database_backup_path(
            filename=nested_directory.name,
            backup_directory=backup_directory,
        )


def test_resolve_encrypted_database_backup_path_rejects_symbolic_link(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    target_path = tmp_path / "outside.db.enc"
    target_path.write_bytes(b"outside backup")

    link_path = backup_directory / "linked.db.enc"

    try:
        link_path.symlink_to(target_path)
    except OSError:
        pytest.skip("Symbolic links are not available in this environment.")

    with pytest.raises(
        BackupError,
        match="must not be a symbolic link",
    ):
        resolve_encrypted_database_backup_path(
            filename=link_path.name,
            backup_directory=backup_directory,
        )


def test_stage_encrypted_database_recovery_creates_valid_staged_copy(
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

    recovery_info = stage_encrypted_database_recovery(
        filename=backup_path.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    staged_path = restore_directory / recovery_info["staged_filename"]
    manifest_path = restore_directory / PENDING_RECOVERY_MANIFEST

    assert recovery_info["backup_filename"] == backup_path.name
    assert recovery_info["staged_filename"].endswith(".restored.db")
    assert recovery_info["staged_at"]
    assert staged_path.exists()
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest == recovery_info

    with sqlite3.connect(staged_path) as conn:
        integrity_result = conn.execute("PRAGMA quick_check").fetchone()

    assert integrity_result is not None
    assert integrity_result[0] == "ok"


def test_stage_encrypted_database_recovery_rejects_second_pending_recovery(
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

    first_recovery = stage_encrypted_database_recovery(
        filename=backup_path.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    with pytest.raises(
        BackupError,
        match="already staged",
    ):
        stage_encrypted_database_recovery(
            filename=backup_path.name,
            backup_directory=backup_directory,
            restore_directory=restore_directory,
        )

    assert (restore_directory / first_recovery["staged_filename"]).exists()


def test_stage_encrypted_database_recovery_rejects_unsafe_filename(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"
    backup_directory.mkdir()

    with pytest.raises(
        BackupError,
        match="Invalid backup filename",
    ):
        stage_encrypted_database_recovery(
            filename="../outside.db.enc",
            backup_directory=backup_directory,
            restore_directory=restore_directory,
        )

    assert not restore_directory.exists()


def test_stage_encrypted_database_recovery_does_not_modify_active_database(
    tmp_path,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    init_db()

    original_database_bytes = database_path.read_bytes()

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    stage_encrypted_database_recovery(
        filename=backup_path.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    assert database_path.read_bytes() == original_database_bytes


def test_get_staged_database_recovery_returns_pending_recovery(
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

    staged_recovery = stage_encrypted_database_recovery(
        filename=backup_path.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    result = get_staged_database_recovery(
        restore_directory=restore_directory,
    )

    assert result == staged_recovery


def test_get_staged_database_recovery_returns_none_when_absent(
    tmp_path,
):
    result = get_staged_database_recovery(
        restore_directory=tmp_path / "restores",
    )

    assert result is None


def test_get_staged_database_recovery_rejects_invalid_manifest(
    tmp_path,
):
    restore_directory = tmp_path / "restores"
    restore_directory.mkdir()

    manifest_path = restore_directory / PENDING_RECOVERY_MANIFEST
    manifest_path.write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        BackupError,
        match="Pending recovery manifest is invalid",
    ):
        get_staged_database_recovery(
            restore_directory=restore_directory,
        )


def test_get_staged_database_recovery_rejects_missing_staged_database(
    tmp_path,
):
    restore_directory = tmp_path / "restores"
    restore_directory.mkdir()

    manifest_path = restore_directory / PENDING_RECOVERY_MANIFEST
    manifest_path.write_text(
        json.dumps(
            {
                "backup_filename": "backup.db.enc",
                "staged_filename": "missing.restored.db",
                "staged_at": "2026-07-28T04:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        BackupError,
        match="Staged recovery database does not exist",
    ):
        get_staged_database_recovery(
            restore_directory=restore_directory,
        )


def test_get_staged_database_recovery_rejects_unsafe_staged_filename(
    tmp_path,
):
    restore_directory = tmp_path / "restores"
    restore_directory.mkdir()

    manifest_path = restore_directory / PENDING_RECOVERY_MANIFEST
    manifest_path.write_text(
        json.dumps(
            {
                "backup_filename": "backup.db.enc",
                "staged_filename": "../outside.restored.db",
                "staged_at": "2026-07-28T04:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        BackupError,
        match="Pending recovery manifest is invalid",
    ):
        get_staged_database_recovery(
            restore_directory=restore_directory,
        )


def test_cancel_staged_database_recovery_removes_pending_files(
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

    staged_recovery = stage_encrypted_database_recovery(
        filename=backup_path.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    result = cancel_staged_database_recovery(
        restore_directory=restore_directory,
    )

    assert result == staged_recovery
    assert not (restore_directory / staged_recovery["staged_filename"]).exists()
    assert not (restore_directory / PENDING_RECOVERY_MANIFEST).exists()

    assert (
        get_staged_database_recovery(
            restore_directory=restore_directory,
        )
        is None
    )


def test_cancel_staged_database_recovery_rejects_missing_pending_recovery(
    tmp_path,
):
    with pytest.raises(
        BackupError,
        match="No database recovery is currently staged",
    ):
        cancel_staged_database_recovery(
            restore_directory=tmp_path / "restores",
        )


def test_cancel_staged_database_recovery_does_not_modify_active_database(
    tmp_path,
):
    database_path = tmp_path / "auth_tracker.db"
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    init_db()

    original_database_bytes = database_path.read_bytes()

    backup_path = create_encrypted_database_backup(
        database_path=database_path,
        backup_directory=backup_directory,
    )

    stage_encrypted_database_recovery(
        filename=backup_path.name,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
    )

    cancel_staged_database_recovery(
        restore_directory=restore_directory,
    )

    assert database_path.read_bytes() == original_database_bytes
