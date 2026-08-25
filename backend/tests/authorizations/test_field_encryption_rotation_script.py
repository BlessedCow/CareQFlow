from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scripts import rotate_field_encryption_key


@pytest.fixture(autouse=True)
def isolate_script_environment(monkeypatch):
    monkeypatch.setattr(
        rotate_field_encryption_key,
        "configure_environment",
        lambda: None,
    )


def test_main_requires_confirmation(monkeypatch, capsys):
    rotation_called = False

    def run_rotation(
        *,
        username: str | None = None,
    ) -> tuple[Path, dict[str, int]]:
        nonlocal rotation_called
        rotation_called = True

        return Path("backup.enc"), {
            "authorization_fields": 1,
            "event_notes": 1,
            "mfa_secrets": 1,
            "documents": 1,
        }

    monkeypatch.setattr(
        rotate_field_encryption_key,
        "back_up_and_rotate_field_encryption_data",
        run_rotation,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["rotate_field_encryption_key.py"],
    )

    assert rotate_field_encryption_key.main() == 1
    assert rotation_called is False

    captured = capsys.readouterr()
    assert "Pass --confirm" in captured.err


def test_main_reports_backup_and_rotation_counts(
    monkeypatch,
    capsys,
    tmp_path,
):
    backup_path = tmp_path / "auth_tracker_20260825.db.enc"

    def run_rotation(
        *,
        username: str | None = None,
    ) -> tuple[Path, dict[str, int]]:
        assert username == "rotation-admin"

        return backup_path, {
            "authorization_fields": 12,
            "event_notes": 4,
            "mfa_secrets": 2,
            "documents": 3,
        }

    monkeypatch.setattr(
        rotate_field_encryption_key,
        "back_up_and_rotate_field_encryption_data",
        run_rotation,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rotate_field_encryption_key.py",
            "--confirm",
            "--username",
            "rotation-admin",
        ],
    )

    assert rotate_field_encryption_key.main() == 0

    captured = capsys.readouterr()

    assert captured.err == ""
    assert f"Created and verified encrypted backup: {backup_path}" in captured.out
    assert "Rotated authorization fields: 12" in captured.out
    assert "Rotated authorization event notes: 4" in captured.out
    assert "Rotated MFA secrets: 2" in captured.out
    assert "Rotated authorization documents: 3" in captured.out


@pytest.mark.parametrize(
    "error",
    [
        rotate_field_encryption_key.BackupConfigError("backup configuration failed"),
        rotate_field_encryption_key.BackupError("backup creation failed"),
        rotate_field_encryption_key.DecryptionError("field rotation failed"),
        rotate_field_encryption_key.EncryptionConfigError(
            "rotation configuration failed"
        ),
        RuntimeError("rotation failed"),
    ],
)
def test_main_returns_failure_without_exposing_sensitive_values(
    monkeypatch,
    capsys,
    error,
):
    def run_rotation(
        *,
        username: str | None = None,
    ) -> tuple[Path, dict[str, int]]:
        raise error

    monkeypatch.setattr(
        rotate_field_encryption_key,
        "back_up_and_rotate_field_encryption_data",
        run_rotation,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rotate_field_encryption_key.py",
            "--confirm",
        ],
    )

    assert rotate_field_encryption_key.main() == 1

    captured = capsys.readouterr()

    assert str(error) in captured.err
    assert captured.out == ""


def test_main_reports_completed_rotation_when_audit_recording_fails(
    monkeypatch,
    capsys,
    tmp_path,
):
    backup_path = tmp_path / "auth_tracker_20260825.db.enc"

    counts = {
        "authorization_fields": 12,
        "event_notes": 4,
        "mfa_secrets": 2,
        "documents": 3,
    }

    def run_rotation(
        *,
        username: str | None = None,
    ) -> tuple[Path, dict[str, int]]:
        raise rotate_field_encryption_key.FieldEncryptionRotationAuditError(
            backup_path=backup_path,
            counts=counts,
        )

    monkeypatch.setattr(
        rotate_field_encryption_key,
        "back_up_and_rotate_field_encryption_data",
        run_rotation,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rotate_field_encryption_key.py",
            "--confirm",
            "--username",
            "rotation-admin",
        ],
    )

    assert rotate_field_encryption_key.main() == 2

    captured = capsys.readouterr()

    assert captured.out == ""
    assert "rotation completed successfully" in captured.err
    assert f"Verified pre-rotation backup: {backup_path}" in captured.err
    assert (
        "Do not restore the previous field encryption key "
        "as the current key." in captured.err
    )
