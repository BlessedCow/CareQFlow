from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts import encrypt_authorization_fields


@pytest.fixture(autouse=True)
def isolate_script_environment(monkeypatch):
    monkeypatch.setattr(
        encrypt_authorization_fields,
        "configure_environment",
        lambda: None,
    )


def test_main_requires_confirmation(monkeypatch, capsys):
    migration_called = False

    def run_migration() -> tuple[Path, int]:
        nonlocal migration_called
        migration_called = True
        return Path("backup.enc"), 1

    monkeypatch.setattr(
        encrypt_authorization_fields,
        "back_up_and_encrypt_plaintext_authorization_fields",
        run_migration,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["encrypt_authorization_fields.py"],
    )

    assert encrypt_authorization_fields.main() == 1
    assert migration_called is False

    captured = capsys.readouterr()
    assert "Pass --confirm" in captured.err


def test_main_reports_backup_and_updated_record_count(
    monkeypatch,
    capsys,
    tmp_path,
):
    backup_path = tmp_path / "auth_tracker_20260725.db.enc"

    monkeypatch.setattr(
        encrypt_authorization_fields,
        "back_up_and_encrypt_plaintext_authorization_fields",
        lambda: (backup_path, 4),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["encrypt_authorization_fields.py", "--confirm"],
    )

    assert encrypt_authorization_fields.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert f"Created encrypted backup: {backup_path}" in captured.out
    assert "Encrypted authorization records: 4" in captured.out


@pytest.mark.parametrize(
    "error",
    [
        encrypt_authorization_fields.BackupConfigError("backup configuration failed"),
        encrypt_authorization_fields.BackupError("backup creation failed"),
        RuntimeError("field encryption failed"),
    ],
)
def test_main_returns_failure_without_exposing_record_values(
    monkeypatch,
    capsys,
    error,
):
    def run_migration() -> tuple[Path, int]:
        raise error

    monkeypatch.setattr(
        encrypt_authorization_fields,
        "back_up_and_encrypt_plaintext_authorization_fields",
        run_migration,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["encrypt_authorization_fields.py", "--confirm"],
    )

    assert encrypt_authorization_fields.main() == 1

    captured = capsys.readouterr()
    assert str(error) in captured.err
    assert captured.out == ""
