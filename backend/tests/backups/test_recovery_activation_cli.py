from __future__ import annotations

import sys
from pathlib import Path

import pytest

from authstatus_api.backups.recovery_activation import (
    RECOVERY_CONFIRMATION_PHRASE,
    RecoveryActivationError,
)
from scripts import activate_staged_recovery


@pytest.fixture(autouse=True)
def isolate_cli_environment(monkeypatch):
    monkeypatch.setattr(
        activate_staged_recovery,
        "configure_environment",
        lambda: None,
    )


def build_plan(tmp_path: Path) -> dict:
    return {
        "active_database": tmp_path / "auth_tracker.db",
        "staged_database": (tmp_path / "restores" / "staged.restored.db"),
        "rollback_database": (tmp_path / "auth_tracker.pre_recovery.db"),
        "safety_backup": (tmp_path / "backups" / "safety.db.enc"),
        "sidecars": [],
        "service_name": None,
        "api_host": "127.0.0.1",
        "api_port": 8000,
    }


def test_main_runs_preflight_and_activates_recovery(
    monkeypatch,
    capsys,
    tmp_path,
):
    plan = build_plan(tmp_path)
    result = {
        "active_database": plan["active_database"],
        "rollback_database": plan["rollback_database"],
        "safety_backup": plan["safety_backup"],
    }

    preflight_calls = []
    activation_calls = []

    def prepare_recovery(**kwargs):
        preflight_calls.append(kwargs)
        return plan

    def activate_recovery(*, plan, confirmation):
        activation_calls.append(
            {
                "plan": plan,
                "confirmation": confirmation,
            }
        )
        return result

    monkeypatch.setattr(
        activate_staged_recovery,
        "prepare_recovery_activation",
        prepare_recovery,
    )
    monkeypatch.setattr(
        activate_staged_recovery,
        "format_recovery_activation_plan",
        lambda current_plan: "RECOVERY PLAN",
    )
    monkeypatch.setattr(
        activate_staged_recovery,
        "activate_staged_database_recovery",
        activate_recovery,
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: RECOVERY_CONFIRMATION_PHRASE,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "activate_staged_recovery.py",
            "--database-path",
            str(tmp_path / "auth_tracker.db"),
            "--backup-directory",
            str(tmp_path / "backups"),
            "--restore-directory",
            str(tmp_path / "restores"),
            "--service-name",
            "CareQueue",
            "--api-host",
            "127.0.0.1",
            "--api-port",
            "8000",
        ],
    )

    assert activate_staged_recovery.main() == activate_staged_recovery.EXIT_SUCCESS

    assert preflight_calls == [
        {
            "database_path": tmp_path / "auth_tracker.db",
            "backup_directory": tmp_path / "backups",
            "restore_directory": tmp_path / "restores",
            "service_name": "CareQueue",
            "api_host": "127.0.0.1",
            "api_port": 8000,
        }
    ]
    assert activation_calls == [
        {
            "plan": plan,
            "confirmation": RECOVERY_CONFIRMATION_PHRASE,
        }
    ]

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "RECOVERY PLAN" in captured.out
    assert "Database recovery activated successfully." in captured.out
    assert str(result["active_database"]) in captured.out
    assert str(result["rollback_database"]) in captured.out
    assert str(result["safety_backup"]) in captured.out
    assert "CareQFlow remains stopped." in captured.out


def test_main_returns_failure_when_preflight_fails(
    monkeypatch,
    capsys,
):
    def fail_preflight(**_kwargs):
        raise RecoveryActivationError("port 8000 is still in use")

    monkeypatch.setattr(
        activate_staged_recovery,
        "prepare_recovery_activation",
        fail_preflight,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["activate_staged_recovery.py"],
    )

    assert activate_staged_recovery.main() == activate_staged_recovery.EXIT_FAILURE

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Recovery preflight failed" in captured.err
    assert "port 8000 is still in use" in captured.err


def test_main_cancels_when_confirmation_is_incorrect(
    monkeypatch,
    capsys,
    tmp_path,
):
    activation_called = False
    plan = build_plan(tmp_path)

    monkeypatch.setattr(
        activate_staged_recovery,
        "prepare_recovery_activation",
        lambda **_kwargs: plan,
    )
    monkeypatch.setattr(
        activate_staged_recovery,
        "format_recovery_activation_plan",
        lambda _plan: "RECOVERY PLAN",
    )

    def reject_confirmation(*, plan, confirmation):
        nonlocal activation_called
        activation_called = True

        raise RecoveryActivationError(
            "Recovery activation canceled: the confirmation "
            "phrase did not match exactly."
        )

    monkeypatch.setattr(
        activate_staged_recovery,
        "activate_staged_database_recovery",
        reject_confirmation,
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: "activate recovery",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["activate_staged_recovery.py"],
    )

    assert activate_staged_recovery.main() == activate_staged_recovery.EXIT_CANCELED
    assert activation_called is True

    captured = capsys.readouterr()
    assert "RECOVERY PLAN" in captured.out
    assert "did not match exactly" in captured.err


@pytest.mark.parametrize(
    "input_error",
    [
        EOFError(),
        KeyboardInterrupt(),
    ],
)
def test_main_cancels_when_confirmation_input_is_interrupted(
    monkeypatch,
    capsys,
    tmp_path,
    input_error,
):
    plan = build_plan(tmp_path)

    monkeypatch.setattr(
        activate_staged_recovery,
        "prepare_recovery_activation",
        lambda **_kwargs: plan,
    )
    monkeypatch.setattr(
        activate_staged_recovery,
        "format_recovery_activation_plan",
        lambda _plan: "RECOVERY PLAN",
    )
    monkeypatch.setattr(
        activate_staged_recovery,
        "activate_staged_database_recovery",
        pytest.fail,
    )

    def interrupt_input(_prompt):
        raise input_error

    monkeypatch.setattr(
        "builtins.input",
        interrupt_input,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["activate_staged_recovery.py"],
    )

    assert activate_staged_recovery.main() == activate_staged_recovery.EXIT_CANCELED

    captured = capsys.readouterr()
    assert "RECOVERY PLAN" in captured.out
    assert "canceled before database cutover" in captured.err


def test_main_returns_failure_when_cutover_fails(
    monkeypatch,
    capsys,
    tmp_path,
):
    plan = build_plan(tmp_path)

    monkeypatch.setattr(
        activate_staged_recovery,
        "prepare_recovery_activation",
        lambda **_kwargs: plan,
    )
    monkeypatch.setattr(
        activate_staged_recovery,
        "format_recovery_activation_plan",
        lambda _plan: "RECOVERY PLAN",
    )
    monkeypatch.setattr(
        activate_staged_recovery,
        "activate_staged_database_recovery",
        lambda **_kwargs: (_ for _ in ()).throw(
            RecoveryActivationError("The original database was restored.")
        ),
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda _prompt: RECOVERY_CONFIRMATION_PHRASE,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["activate_staged_recovery.py"],
    )

    assert activate_staged_recovery.main() == activate_staged_recovery.EXIT_FAILURE

    captured = capsys.readouterr()
    assert "RECOVERY PLAN" in captured.out
    assert "Recovery activation failed" in captured.err
    assert "original database was restored" in captured.err
