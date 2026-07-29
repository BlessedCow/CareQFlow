from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from authstatus_api.backups.retention import (
    BackupRetentionError,
    prune_encrypted_database_backups,
)
from authstatus_api.backups.service import PENDING_RECOVERY_MANIFEST
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_backup_retention_settings(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        "AUTHSTATUS_BACKUP_DIRECTORY",
        str(tmp_path / "backups"),
    )
    monkeypatch.setenv(
        "AUTHSTATUS_RESTORE_DIRECTORY",
        str(tmp_path / "restores"),
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def create_backup(
    backup_directory: Path,
    *,
    filename: str,
    modified_at: datetime,
) -> Path:
    backup_directory.mkdir(parents=True, exist_ok=True)

    backup_path = backup_directory / filename
    backup_path.write_bytes(b"encrypted backup")

    timestamp = modified_at.timestamp()
    os.utime(
        backup_path,
        (timestamp, timestamp),
    )

    return backup_path


def test_prune_encrypted_database_backups_deletes_expired_backups(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    reference_time = datetime(
        2026,
        7,
        29,
        12,
        0,
        tzinfo=UTC,
    )

    newest_backup = create_backup(
        backup_directory,
        filename=("auth_tracker.sqlcipher_20260729_120000_000001.db.enc"),
        modified_at=reference_time,
    )
    recent_backup = create_backup(
        backup_directory,
        filename=("auth_tracker.sqlcipher_20260720_120000_000001.db.enc"),
        modified_at=reference_time - timedelta(days=9),
    )
    expired_backup = create_backup(
        backup_directory,
        filename=("auth_tracker.sqlcipher_20260401_120000_000001.db.enc"),
        modified_at=reference_time - timedelta(days=119),
    )

    result = prune_encrypted_database_backups(
        retention_days=90,
        minimum_count=1,
        backup_directory=backup_directory,
        restore_directory=tmp_path / "restores",
        now=reference_time,
    )

    assert result == {
        "deleted": [expired_backup.name],
        "protected": [],
        "retained": [
            newest_backup.name,
            recent_backup.name,
        ],
        "failed": [],
    }
    assert newest_backup.exists()
    assert recent_backup.exists()
    assert not expired_backup.exists()


def test_prune_encrypted_database_backups_preserves_minimum_count(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    reference_time = datetime(
        2026,
        7,
        29,
        12,
        0,
        tzinfo=UTC,
    )

    backup_paths = [
        create_backup(
            backup_directory,
            filename=(f"auth_tracker_2026010{index}_120000_000001.db.enc"),
            modified_at=reference_time - timedelta(days=200 + index),
        )
        for index in range(1, 5)
    ]

    expected_retained = {
        path.name
        for path in sorted(
            backup_paths,
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:2]
    }

    result = prune_encrypted_database_backups(
        retention_days=30,
        minimum_count=2,
        backup_directory=backup_directory,
        restore_directory=tmp_path / "restores",
        now=reference_time,
    )

    assert set(result["retained"]) == expected_retained
    assert len(result["deleted"]) == 2

    for backup_path in backup_paths:
        assert backup_path.exists() is (backup_path.name in expected_retained)


def test_prune_encrypted_database_backups_protects_pending_recovery_source(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"
    reference_time = datetime(
        2026,
        7,
        29,
        12,
        0,
        tzinfo=UTC,
    )

    recent_backup = create_backup(
        backup_directory,
        filename="auth_tracker_20260729_120000_000001.db.enc",
        modified_at=reference_time,
    )
    pending_backup = create_backup(
        backup_directory,
        filename="auth_tracker_20260101_120000_000001.db.enc",
        modified_at=reference_time - timedelta(days=209),
    )
    expired_backup = create_backup(
        backup_directory,
        filename="auth_tracker_20260102_120000_000001.db.enc",
        modified_at=reference_time - timedelta(days=208),
    )

    restore_directory.mkdir(parents=True)
    manifest_path = restore_directory / PENDING_RECOVERY_MANIFEST
    manifest_path.write_text(
        json.dumps(
            {
                "backup_filename": pending_backup.name,
                "staged_filename": "pending.restored.db",
                "staged_at": reference_time.isoformat(),
            }
        ),
        encoding="utf-8",
    )

    result = prune_encrypted_database_backups(
        retention_days=30,
        minimum_count=1,
        backup_directory=backup_directory,
        restore_directory=restore_directory,
        now=reference_time,
    )

    assert result["protected"] == [pending_backup.name]
    assert result["deleted"] == [expired_backup.name]
    assert recent_backup.exists()
    assert pending_backup.exists()
    assert not expired_backup.exists()


def test_prune_encrypted_database_backups_ignores_unrecognized_files(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    reference_time = datetime(
        2026,
        7,
        29,
        12,
        0,
        tzinfo=UTC,
    )

    recognized_backup = create_backup(
        backup_directory,
        filename="auth_tracker_20260101_120000_000001.db.enc",
        modified_at=reference_time - timedelta(days=209),
    )
    unrelated_encrypted_file = create_backup(
        backup_directory,
        filename="manual-export.db.enc",
        modified_at=reference_time - timedelta(days=300),
    )
    plaintext_database = create_backup(
        backup_directory,
        filename="auth_tracker_20260101_120000_000001.db",
        modified_at=reference_time - timedelta(days=300),
    )

    result = prune_encrypted_database_backups(
        retention_days=30,
        minimum_count=1,
        backup_directory=backup_directory,
        restore_directory=tmp_path / "restores",
        now=reference_time,
    )

    assert result["retained"] == [recognized_backup.name]
    assert unrelated_encrypted_file.exists()
    assert plaintext_database.exists()


def test_prune_encrypted_database_backups_ignores_symbolic_links(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    backup_directory.mkdir()

    target_path = tmp_path / "outside.db.enc"
    target_path.write_bytes(b"outside backup")

    symlink_path = backup_directory / "auth_tracker_20200101_120000_000001.db.enc"

    try:
        symlink_path.symlink_to(target_path)
    except OSError:
        pytest.skip("Symbolic links are unavailable in this environment.")

    result = prune_encrypted_database_backups(
        retention_days=30,
        minimum_count=1,
        backup_directory=backup_directory,
        restore_directory=tmp_path / "restores",
        now=datetime(
            2026,
            7,
            29,
            12,
            0,
            tzinfo=UTC,
        ),
    )

    assert result == {
        "deleted": [],
        "protected": [],
        "retained": [],
        "failed": [],
    }
    assert symlink_path.exists()
    assert target_path.exists()


def test_prune_encrypted_database_backups_reports_delete_failure(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    reference_time = datetime(
        2026,
        7,
        29,
        12,
        0,
        tzinfo=UTC,
    )

    recent_backup = create_backup(
        backup_directory,
        filename="auth_tracker_20260729_120000_000001.db.enc",
        modified_at=reference_time,
    )
    expired_backup = create_backup(
        backup_directory,
        filename="auth_tracker_20260101_120000_000001.db.enc",
        modified_at=reference_time - timedelta(days=209),
    )

    with patch.object(
        Path,
        "unlink",
        side_effect=OSError("access denied"),
    ):
        result = prune_encrypted_database_backups(
            retention_days=30,
            minimum_count=1,
            backup_directory=backup_directory,
            restore_directory=tmp_path / "restores",
            now=reference_time,
        )

    assert result["deleted"] == []
    assert result["retained"] == [recent_backup.name]
    assert result["failed"] == [
        {
            "filename": expired_backup.name,
            "reason": "access denied",
        }
    ]
    assert expired_backup.exists()


@pytest.mark.parametrize(
    ("retention_days", "minimum_count", "message"),
    [
        (0, 1, "retention days must be at least 1"),
        (-1, 1, "retention days must be at least 1"),
        (30, 0, "Minimum retained backup count must be at least 1"),
        (30, -1, "Minimum retained backup count must be at least 1"),
    ],
)
def test_prune_encrypted_database_backups_rejects_unsafe_values(
    retention_days,
    minimum_count,
    message,
):
    with pytest.raises(
        BackupRetentionError,
        match=message,
    ):
        prune_encrypted_database_backups(
            retention_days=retention_days,
            minimum_count=minimum_count,
        )


def test_prune_encrypted_database_backups_rejects_naive_reference_time(
    tmp_path,
):
    with pytest.raises(
        BackupRetentionError,
        match="reference time must include a timezone",
    ):
        prune_encrypted_database_backups(
            retention_days=90,
            minimum_count=5,
            backup_directory=tmp_path / "backups",
            restore_directory=tmp_path / "restores",
            now=datetime(2026, 7, 29, 12, 0),
        )


def test_prune_encrypted_database_backups_rejects_invalid_pending_manifest(
    tmp_path,
):
    backup_directory = tmp_path / "backups"
    restore_directory = tmp_path / "restores"

    backup_directory.mkdir()
    restore_directory.mkdir()

    (restore_directory / PENDING_RECOVERY_MANIFEST).write_text(
        "not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        BackupRetentionError,
        match="Unable to read the pending recovery manifest",
    ):
        prune_encrypted_database_backups(
            retention_days=90,
            minimum_count=5,
            backup_directory=backup_directory,
            restore_directory=restore_directory,
        )
