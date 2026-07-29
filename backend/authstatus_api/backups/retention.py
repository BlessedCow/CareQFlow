from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypedDict

from authstatus_api.backups.service import PENDING_RECOVERY_MANIFEST
from authstatus_api.settings import get_settings, resolve_project_path


class BackupRetentionError(RuntimeError):
    pass


class BackupPruneFailure(TypedDict):
    filename: str
    reason: str


class BackupPruneResult(TypedDict):
    deleted: list[str]
    protected: list[str]
    retained: list[str]
    failed: list[BackupPruneFailure]


CAREQUEUE_BACKUP_FILENAME_PATTERN = re.compile(r"^.+_\d{8}_\d{6}_\d{6}\.db\.enc$")


def _read_pending_recovery_backup_filename(
    *,
    restore_directory: Path,
) -> str | None:
    manifest_path = restore_directory / PENDING_RECOVERY_MANIFEST

    if not manifest_path.exists():
        return None

    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise BackupRetentionError("Pending recovery manifest must be a regular file.")

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupRetentionError(
            "Unable to read the pending recovery manifest."
        ) from exc

    if not isinstance(manifest_data, dict):
        raise BackupRetentionError("Pending recovery manifest is invalid.")

    backup_filename = manifest_data.get("backup_filename")

    if not isinstance(backup_filename, str) or not backup_filename:
        raise BackupRetentionError(
            "Pending recovery manifest does not contain a valid " "backup filename."
        )

    if Path(backup_filename).name != backup_filename:
        raise BackupRetentionError(
            "Pending recovery manifest contains an invalid " "backup filename."
        )

    return backup_filename


def prune_encrypted_database_backups(
    *,
    retention_days: int,
    minimum_count: int,
    backup_directory: Path | None = None,
    restore_directory: Path | None = None,
    now: datetime | None = None,
) -> BackupPruneResult:
    if retention_days < 1:
        raise BackupRetentionError("Backup retention days must be at least 1.")

    if minimum_count < 1:
        raise BackupRetentionError("Minimum retained backup count must be at least 1.")

    settings = get_settings()
    source_directory = resolve_project_path(
        backup_directory or settings.backup_directory
    )
    recovery_directory = resolve_project_path(
        restore_directory or settings.restore_directory
    )

    reference_time = now or datetime.now(UTC)

    if reference_time.tzinfo is None or reference_time.utcoffset() is None:
        raise BackupRetentionError(
            "Backup retention reference time must include a timezone."
        )

    cutoff = reference_time.astimezone(UTC) - timedelta(days=retention_days)

    if not source_directory.exists():
        return {
            "deleted": [],
            "protected": [],
            "retained": [],
            "failed": [],
        }

    if not source_directory.is_dir():
        raise BackupRetentionError("Backup directory path is not a directory.")

    pending_backup_filename = _read_pending_recovery_backup_filename(
        restore_directory=recovery_directory,
    )

    backup_paths: list[Path] = []

    for backup_path in source_directory.iterdir():
        if backup_path.is_symlink():
            continue

        if not backup_path.is_file():
            continue

        if not CAREQUEUE_BACKUP_FILENAME_PATTERN.fullmatch(backup_path.name):
            continue

        backup_paths.append(backup_path)

    backup_paths.sort(
        key=lambda path: (
            path.stat().st_mtime,
            path.name,
        ),
        reverse=True,
    )

    minimum_retained_paths = set(backup_paths[:minimum_count])

    deleted: list[str] = []
    protected: list[str] = []
    retained: list[str] = []
    failed: list[BackupPruneFailure] = []

    for backup_path in backup_paths:
        if backup_path.name == pending_backup_filename:
            protected.append(backup_path.name)
            continue

        if backup_path in minimum_retained_paths:
            retained.append(backup_path.name)
            continue

        modified_at = datetime.fromtimestamp(
            backup_path.stat().st_mtime,
            tz=UTC,
        )

        if modified_at >= cutoff:
            retained.append(backup_path.name)
            continue

        try:
            backup_path.unlink()
        except OSError as exc:
            failed.append(
                {
                    "filename": backup_path.name,
                    "reason": str(exc),
                }
            )
        else:
            deleted.append(backup_path.name)

    return {
        "deleted": deleted,
        "protected": protected,
        "retained": retained,
        "failed": failed,
    }
