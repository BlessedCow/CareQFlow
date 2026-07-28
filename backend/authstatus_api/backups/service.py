from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

from cryptography.fernet import Fernet, InvalidToken

from authstatus_api.database_encryption.sqlcipher_probe import (
    apply_sqlcipher_key,
    import_sqlcipher,
)
from authstatus_api.persistence.paths import get_database_path
from authstatus_api.settings import get_settings, resolve_project_path


class BackupConfigError(RuntimeError):
    pass


class BackupError(RuntimeError):
    pass


class BackupFileInfo(TypedDict):
    filename: str
    size_bytes: int
    created_at: str


class StagedRecoveryInfo(TypedDict):
    backup_filename: str
    staged_filename: str
    staged_at: str


REQUIRED_DATABASE_TABLES = {
    "audit_events",
    "auth_events",
    "auths",
    "sessions",
    "users",
}


PENDING_RECOVERY_MANIFEST = "pending_recovery.json"


def _backup_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")


def _get_backup_fernet() -> Fernet:
    key = get_settings().backup_encryption_key.strip()

    if not key:
        raise BackupConfigError("Missing AUTHSTATUS_BACKUP_ENCRYPTION_KEY.")

    try:
        return Fernet(key.encode("utf-8"))
    except ValueError as exc:
        raise BackupConfigError("Invalid AUTHSTATUS_BACKUP_ENCRYPTION_KEY.") from exc


def _atomic_write_bytes(destination_path: Path, data: bytes) -> None:
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination_path.parent,
            prefix=f".{destination_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)

        temporary_path.replace(destination_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _create_plaintext_snapshot(
    source_path: Path,
    snapshot_path: Path,
) -> None:
    source_conn: sqlite3.Connection | None = None
    snapshot_conn: sqlite3.Connection | None = None

    try:
        source_conn = sqlite3.connect(source_path)
        snapshot_conn = sqlite3.connect(snapshot_path)
        source_conn.backup(snapshot_conn)
    except sqlite3.DatabaseError as exc:
        raise BackupError(
            "Unable to create a consistent plaintext database snapshot."
        ) from exc
    finally:
        if snapshot_conn is not None:
            snapshot_conn.close()

        if source_conn is not None:
            source_conn.close()


def _create_sqlcipher_snapshot(
    source_path: Path,
    snapshot_path: Path,
    *,
    passphrase: str,
) -> None:
    if not passphrase:
        raise BackupConfigError(
            "AUTHSTATUS_SQLCIPHER_KEY is required to back up a SQLCipher database."
        )

    sqlcipher3 = import_sqlcipher()
    source_conn: Any | None = None
    snapshot_conn: Any | None = None

    try:
        source_conn = sqlcipher3.connect(str(source_path))
        apply_sqlcipher_key(source_conn, passphrase)

        snapshot_conn = sqlcipher3.connect(str(snapshot_path))
        apply_sqlcipher_key(snapshot_conn, passphrase)

        source_conn.backup(snapshot_conn)
    except Exception as exc:
        if isinstance(exc, BackupConfigError):
            raise

        raise BackupError(
            "Unable to create a consistent SQLCipher database snapshot."
        ) from exc
    finally:
        if snapshot_conn is not None:
            snapshot_conn.close()

        if source_conn is not None:
            source_conn.close()


def _create_database_snapshot(
    source_path: Path,
    snapshot_path: Path,
) -> None:
    settings = get_settings()

    if settings.database_encryption == "plaintext":
        _create_plaintext_snapshot(source_path, snapshot_path)
        return

    if settings.database_encryption == "sqlcipher":
        _create_sqlcipher_snapshot(
            source_path,
            snapshot_path,
            passphrase=settings.sqlcipher_key.strip(),
        )
        return

    raise BackupConfigError(
        "Unsupported AUTHSTATUS_DATABASE_ENCRYPTION value: "
        f"{settings.database_encryption}"
    )


def _read_integrity_result(conn: Any) -> str:
    row = conn.execute("PRAGMA quick_check").fetchone()

    if row is None:
        raise BackupError("Restored database integrity check returned no result.")

    return str(row[0])


def _read_table_names(conn: Any) -> set[str]:
    rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        """).fetchall()

    return {str(row[0]) for row in rows}


def _validate_database_connection(conn: Any) -> None:
    integrity_result = _read_integrity_result(conn)

    if integrity_result.lower() != "ok":
        raise BackupError(
            f"Restored database failed its integrity check: {integrity_result}"
        )

    table_names = _read_table_names(conn)
    missing_tables = sorted(REQUIRED_DATABASE_TABLES - table_names)

    if missing_tables:
        raise BackupError(
            "Restored database is missing required CareQueue tables: "
            f"{missing_tables}"
        )


def _validate_plaintext_database(database_path: Path) -> None:
    try:
        conn = sqlite3.connect(database_path)
        try:
            _validate_database_connection(conn)
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise BackupError(
            "Restored file is not a valid plaintext SQLite database."
        ) from exc


def _validate_sqlcipher_database(
    database_path: Path,
    *,
    passphrase: str,
) -> None:
    if not passphrase:
        raise BackupConfigError(
            "AUTHSTATUS_SQLCIPHER_KEY is required to validate a SQLCipher restore."
        )

    sqlcipher3 = import_sqlcipher()

    try:
        conn = sqlcipher3.connect(str(database_path))
        try:
            apply_sqlcipher_key(conn, passphrase)
            _validate_database_connection(conn)
        finally:
            conn.close()
    except Exception as exc:
        if isinstance(exc, (BackupConfigError, BackupError)):
            raise

        raise BackupError(
            "Restored file is not a valid SQLCipher database for the configured key."
        ) from exc


def _validate_restored_database(database_path: Path) -> None:
    settings = get_settings()

    if settings.database_encryption == "plaintext":
        _validate_plaintext_database(database_path)
        return

    if settings.database_encryption == "sqlcipher":
        _validate_sqlcipher_database(
            database_path,
            passphrase=settings.sqlcipher_key.strip(),
        )
        return

    raise BackupConfigError(
        "Unsupported AUTHSTATUS_DATABASE_ENCRYPTION value: "
        f"{settings.database_encryption}"
    )


def encrypt_backup_bytes(database_bytes: bytes) -> bytes:
    return _get_backup_fernet().encrypt(database_bytes)


def decrypt_backup_bytes(encrypted_bytes: bytes) -> bytes:
    try:
        return _get_backup_fernet().decrypt(encrypted_bytes)
    except InvalidToken as exc:
        raise BackupError("Unable to decrypt backup file.") from exc


def list_encrypted_database_backups(
    *,
    backup_directory: Path | None = None,
) -> list[BackupFileInfo]:
    settings = get_settings()
    source_directory = resolve_project_path(
        backup_directory or settings.backup_directory
    )

    if not source_directory.exists():
        return []

    if not source_directory.is_dir():
        raise BackupError(
            f"Backup directory path is not a directory: {source_directory}"
        )

    backups: list[BackupFileInfo] = []

    for backup_path in source_directory.iterdir():
        if (
            not backup_path.is_file()
            or backup_path.name.startswith(".")
            or not backup_path.name.endswith(".db.enc")
        ):
            continue

        file_stat = backup_path.stat()

        backups.append(
            {
                "filename": backup_path.name,
                "size_bytes": file_stat.st_size,
                "created_at": datetime.fromtimestamp(
                    file_stat.st_mtime,
                    tz=UTC,
                ).isoformat(timespec="seconds"),
            }
        )

    return sorted(
        backups,
        key=lambda backup: (
            backup["created_at"],
            backup["filename"],
        ),
        reverse=True,
    )


def resolve_encrypted_database_backup_path(
    *,
    filename: str,
    backup_directory: Path | None = None,
) -> Path:
    settings = get_settings()
    source_directory = resolve_project_path(
        backup_directory or settings.backup_directory
    )

    if not filename or filename in {".", ".."}:
        raise BackupError("Invalid backup filename.")

    if (
        "\x00" in filename
        or "/" in filename
        or "\\" in filename
        or Path(filename).name != filename
        or filename.startswith(".")
        or not filename.endswith(".db.enc")
    ):
        raise BackupError("Invalid backup filename.")

    if not source_directory.exists():
        raise BackupError("Backup directory does not exist.")

    if not source_directory.is_dir():
        raise BackupError("Backup directory path is not a directory.")

    backup_path = source_directory / filename

    if backup_path.is_symlink():
        raise BackupError("Backup file must not be a symbolic link.")

    if not backup_path.exists():
        raise BackupError("Backup file does not exist.")

    if not backup_path.is_file():
        raise BackupError("Backup path is not a file.")

    resolved_directory = source_directory.resolve()
    resolved_backup_path = backup_path.resolve()

    if resolved_backup_path.parent != resolved_directory:
        raise BackupError("Invalid backup filename.")

    return resolved_backup_path


def create_encrypted_database_backup(
    *,
    database_path: Path | None = None,
    backup_directory: Path | None = None,
) -> Path:
    settings = get_settings()
    source_path = database_path or get_database_path()
    destination_directory = resolve_project_path(
        backup_directory or settings.backup_directory
    )

    if not source_path.exists():
        raise BackupError(f"Database file does not exist: {source_path}")

    if not source_path.is_file():
        raise BackupError(f"Database path is not a file: {source_path}")

    destination_directory.mkdir(parents=True, exist_ok=True)

    snapshot_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            dir=destination_directory,
            prefix=f".{source_path.stem}.snapshot.",
            suffix=source_path.suffix,
            delete=False,
        ) as snapshot_file:
            snapshot_path = Path(snapshot_file.name)

        _create_database_snapshot(source_path, snapshot_path)

        encrypted_bytes = encrypt_backup_bytes(snapshot_path.read_bytes())
        backup_path = destination_directory / (
            f"{source_path.stem}_{_backup_timestamp()}{source_path.suffix}.enc"
        )

        _atomic_write_bytes(backup_path, encrypted_bytes)
    finally:
        if snapshot_path is not None and snapshot_path.exists():
            snapshot_path.unlink()

    return backup_path


def decrypt_backup_file(backup_path: Path) -> bytes:
    if not backup_path.exists():
        raise BackupError(f"Backup file does not exist: {backup_path}")

    return decrypt_backup_bytes(backup_path.read_bytes())


def verify_encrypted_database_backup(
    *,
    backup_path: Path,
) -> None:
    if backup_path.suffix != ".enc":
        raise BackupError(f"Backup file must end with .enc: {backup_path}")

    if not backup_path.exists():
        raise BackupError(f"Backup file does not exist: {backup_path}")

    if not backup_path.is_file():
        raise BackupError(f"Backup path is not a file: {backup_path}")

    if backup_path.stat().st_size == 0:
        raise BackupError(f"Backup file is empty: {backup_path}")

    decrypted_bytes = decrypt_backup_file(backup_path)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=backup_path.parent,
            prefix=f".{backup_path.name}.verify.",
            suffix=".db",
            delete=False,
        ) as temporary_file:
            temporary_file.write(decrypted_bytes)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)

        _validate_restored_database(temporary_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def restore_encrypted_database_backup(
    *,
    backup_path: Path,
    restore_directory: Path | None = None,
) -> Path:
    settings = get_settings()
    destination_directory = resolve_project_path(
        restore_directory or settings.restore_directory
    )

    if backup_path.suffix != ".enc":
        raise BackupError(f"Backup file must end with .enc: {backup_path}")

    decrypted_bytes = decrypt_backup_file(backup_path)

    destination_directory.mkdir(parents=True, exist_ok=True)

    restored_name = backup_path.name.removesuffix(".enc").replace(
        ".db",
        ".restored.db",
    )
    restored_path = destination_directory / restored_name

    if restored_path.exists():
        restored_path = destination_directory / (
            f"{Path(restored_name).stem}_{_backup_timestamp()}.db"
        )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination_directory,
            prefix=f".{restored_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(decrypted_bytes)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)

        _validate_restored_database(temporary_path)
        temporary_path.replace(restored_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return restored_path


def stage_encrypted_database_recovery(
    *,
    filename: str,
    backup_directory: Path | None = None,
    restore_directory: Path | None = None,
) -> StagedRecoveryInfo:
    settings = get_settings()
    destination_directory = resolve_project_path(
        restore_directory or settings.restore_directory
    )
    manifest_path = destination_directory / PENDING_RECOVERY_MANIFEST

    if manifest_path.exists():
        raise BackupError("A database recovery is already staged.")

    backup_path = resolve_encrypted_database_backup_path(
        filename=filename,
        backup_directory=backup_directory,
    )

    verify_encrypted_database_backup(
        backup_path=backup_path,
    )

    staged_path = restore_encrypted_database_backup(
        backup_path=backup_path,
        restore_directory=destination_directory,
    )

    staged_at = datetime.now(UTC).isoformat(timespec="seconds")

    recovery_info: StagedRecoveryInfo = {
        "backup_filename": backup_path.name,
        "staged_filename": staged_path.name,
        "staged_at": staged_at,
    }

    try:
        _atomic_write_bytes(
            manifest_path,
            json.dumps(
                recovery_info,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        )
    except Exception:
        if staged_path.exists():
            staged_path.unlink()

        raise

    return recovery_info


def get_staged_database_recovery(
    *,
    restore_directory: Path | None = None,
) -> StagedRecoveryInfo | None:
    settings = get_settings()
    destination_directory = resolve_project_path(
        restore_directory or settings.restore_directory
    )
    manifest_path = destination_directory / PENDING_RECOVERY_MANIFEST

    if not manifest_path.exists():
        return None

    if not manifest_path.is_file():
        raise BackupError("Pending recovery manifest is not a file.")

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackupError("Pending recovery manifest is invalid.") from exc

    if not isinstance(manifest_data, dict):
        raise BackupError("Pending recovery manifest is invalid.")

    expected_keys = {
        "backup_filename",
        "staged_filename",
        "staged_at",
    }

    if set(manifest_data) != expected_keys:
        raise BackupError("Pending recovery manifest is invalid.")

    if not all(
        isinstance(manifest_data[key], str) and manifest_data[key]
        for key in expected_keys
    ):
        raise BackupError("Pending recovery manifest is invalid.")

    staged_filename = manifest_data["staged_filename"]

    if (
        "\x00" in staged_filename
        or "/" in staged_filename
        or "\\" in staged_filename
        or Path(staged_filename).name != staged_filename
        or staged_filename.startswith(".")
        or not staged_filename.endswith(".restored.db")
    ):
        raise BackupError("Pending recovery manifest is invalid.")

    staged_path = destination_directory / staged_filename

    if staged_path.is_symlink():
        raise BackupError("Staged recovery file must not be a symbolic link.")

    if not staged_path.exists() or not staged_path.is_file():
        raise BackupError("Staged recovery database does not exist.")

    resolved_directory = destination_directory.resolve()
    resolved_staged_path = staged_path.resolve()

    if resolved_staged_path.parent != resolved_directory:
        raise BackupError("Pending recovery manifest is invalid.")

    _validate_restored_database(resolved_staged_path)

    return {
        "backup_filename": manifest_data["backup_filename"],
        "staged_filename": staged_filename,
        "staged_at": manifest_data["staged_at"],
    }


def cancel_staged_database_recovery(
    *,
    restore_directory: Path | None = None,
) -> StagedRecoveryInfo:
    recovery_info = get_staged_database_recovery(
        restore_directory=restore_directory,
    )

    if recovery_info is None:
        raise BackupError("No database recovery is currently staged.")

    settings = get_settings()
    destination_directory = resolve_project_path(
        restore_directory or settings.restore_directory
    )
    staged_path = destination_directory / recovery_info["staged_filename"]
    manifest_path = destination_directory / PENDING_RECOVERY_MANIFEST

    staged_path.unlink()
    manifest_path.unlink()

    return recovery_info
