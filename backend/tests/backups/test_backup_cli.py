from __future__ import annotations

import sys

import pytest

from authstatus_api.backups.retention import BackupRetentionError
from authstatus_api.backups.service import BackupError
from scripts import create_encrypted_backup


@pytest.fixture(autouse=True)
def isolate_backup_cli_settings(
    monkeypatch,
):
    monkeypatch.setattr(
        create_encrypted_backup,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "backup_retention_days": 90,
                "backup_minimum_count": 5,
            },
        )(),
    )


def test_main_creates_verifies_and_prunes_backup(
    monkeypatch,
    capsys,
    tmp_path,
):
    backup_path = tmp_path / "backups" / "backup.db.enc"
    create_calls = []
    verify_calls = []
    prune_calls = []

    monkeypatch.setattr(
        create_encrypted_backup,
        "create_encrypted_database_backup",
        lambda **kwargs: (
            create_calls.append(kwargs),
            backup_path,
        )[1],
    )
    monkeypatch.setattr(
        create_encrypted_backup,
        "verify_encrypted_database_backup",
        lambda **kwargs: verify_calls.append(kwargs),
    )
    monkeypatch.setattr(
        create_encrypted_backup,
        "prune_encrypted_database_backups",
        lambda **kwargs: (
            prune_calls.append(kwargs),
            {
                "deleted": ["expired.db.enc"],
                "protected": ["pending.db.enc"],
                "retained": ["backup.db.enc"],
                "failed": [],
            },
        )[1],
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "create_encrypted_backup.py",
            "--database-path",
            str(tmp_path / "data" / "auth_tracker.db"),
            "--backup-directory",
            str(tmp_path / "backups"),
        ],
    )

    assert create_encrypted_backup.main() == 0

    assert create_calls == [
        {
            "database_path": tmp_path / "data" / "auth_tracker.db",
            "backup_directory": tmp_path / "backups",
        }
    ]
    assert verify_calls == [
        {
            "backup_path": backup_path,
        }
    ]
    assert prune_calls == [
        {
            "retention_days": 90,
            "minimum_count": 5,
            "backup_directory": tmp_path / "backups",
        }
    ]

    captured = capsys.readouterr()
    assert captured.err == ""
    assert f"Created and verified encrypted backup: {backup_path}" in captured.out
    assert "Pruned encrypted backups: expired.db.enc" in captured.out
    assert "Protected by pending recovery: pending.db.enc" in captured.out


def test_main_reports_when_no_backups_are_pruned(
    monkeypatch,
    capsys,
    tmp_path,
):
    backup_path = tmp_path / "backup.db.enc"

    monkeypatch.setattr(
        create_encrypted_backup,
        "create_encrypted_database_backup",
        lambda **_kwargs: backup_path,
    )
    monkeypatch.setattr(
        create_encrypted_backup,
        "verify_encrypted_database_backup",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        create_encrypted_backup,
        "prune_encrypted_database_backups",
        lambda **_kwargs: {
            "deleted": [],
            "protected": [],
            "retained": [backup_path.name],
            "failed": [],
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["create_encrypted_backup.py"],
    )

    assert create_encrypted_backup.main() == 0

    captured = capsys.readouterr()
    assert "No encrypted backups were eligible for pruning." in captured.out
    assert captured.err == ""


def test_main_does_not_prune_when_backup_creation_fails(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        create_encrypted_backup,
        "create_encrypted_database_backup",
        lambda **_kwargs: (_ for _ in ()).throw(BackupError("backup creation failed")),
    )

    prune_calls = []

    monkeypatch.setattr(
        create_encrypted_backup,
        "prune_encrypted_database_backups",
        lambda **kwargs: prune_calls.append(kwargs),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["create_encrypted_backup.py"],
    )

    assert create_encrypted_backup.main() == 1
    assert prune_calls == []

    captured = capsys.readouterr()
    assert "backup creation failed" in captured.err
    assert captured.out == ""


def test_main_returns_retention_failure_after_successful_backup(
    monkeypatch,
    capsys,
    tmp_path,
):
    backup_path = tmp_path / "backup.db.enc"

    monkeypatch.setattr(
        create_encrypted_backup,
        "create_encrypted_database_backup",
        lambda **_kwargs: backup_path,
    )
    monkeypatch.setattr(
        create_encrypted_backup,
        "verify_encrypted_database_backup",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        create_encrypted_backup,
        "prune_encrypted_database_backups",
        lambda **_kwargs: (_ for _ in ()).throw(
            BackupRetentionError("retention failed")
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["create_encrypted_backup.py"],
    )

    assert create_encrypted_backup.main() == 2

    captured = capsys.readouterr()
    assert f"Created and verified encrypted backup: {backup_path}" in captured.out
    assert "Backup retention cleanup failed: retention failed" in captured.err


def test_main_reports_individual_prune_failures(
    monkeypatch,
    capsys,
    tmp_path,
):
    backup_path = tmp_path / "backup.db.enc"

    monkeypatch.setattr(
        create_encrypted_backup,
        "create_encrypted_database_backup",
        lambda **_kwargs: backup_path,
    )
    monkeypatch.setattr(
        create_encrypted_backup,
        "verify_encrypted_database_backup",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        create_encrypted_backup,
        "prune_encrypted_database_backups",
        lambda **_kwargs: {
            "deleted": [],
            "protected": [],
            "retained": [backup_path.name],
            "failed": [
                {
                    "filename": "expired.db.enc",
                    "reason": "access denied",
                }
            ],
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["create_encrypted_backup.py"],
    )

    assert create_encrypted_backup.main() == 2

    captured = capsys.readouterr()
    assert "Unable to prune expired.db.enc: access denied" in captured.err
