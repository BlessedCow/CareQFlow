from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from authstatus_api.backups.recovery_activation import (
    RecoveryActivationError,
    find_database_sidecars,
    require_same_filesystem,
    resolve_recovery_activation_paths,
    verify_api_port_available,
    verify_exclusive_database_access,
    verify_managed_service_stopped,
)
from authstatus_api.backups.service import (
    create_encrypted_database_backup,
    stage_encrypted_database_recovery,
)
from authstatus_api.crypto import generate_encryption_key
from authstatus_api.persistence.schema import init_db
from authstatus_api.settings import get_settings


@pytest.fixture(autouse=True)
def configure_recovery_activation_settings(
    tmp_path,
    monkeypatch,
):
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
    monkeypatch.setenv(
        "AUTHSTATUS_DATABASE_ENCRYPTION",
        "plaintext",
    )
    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def create_staged_recovery(tmp_path):
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

    return database_path, restore_directory, recovery_info


def test_resolve_recovery_activation_paths_returns_safe_paths(
    tmp_path,
):
    database_path, restore_directory, recovery_info = create_staged_recovery(tmp_path)

    paths = resolve_recovery_activation_paths(
        database_path=database_path,
        restore_directory=restore_directory,
    )

    assert paths["active_database"] == database_path.resolve()
    assert (
        paths["staged_database"]
        == (restore_directory / recovery_info["staged_filename"]).resolve()
    )
    assert (
        paths["rollback_database"]
        == (tmp_path / "auth_tracker.pre_recovery.db").resolve()
    )


def test_resolve_recovery_activation_paths_requires_pending_recovery(
    tmp_path,
):
    database_path = tmp_path / "auth_tracker.db"
    database_path.write_bytes(b"database")

    with pytest.raises(
        RecoveryActivationError,
        match="No database recovery is currently staged",
    ):
        resolve_recovery_activation_paths(
            database_path=database_path,
            restore_directory=tmp_path / "restores",
        )


def test_resolve_recovery_activation_paths_rejects_existing_rollback(
    tmp_path,
):
    database_path, restore_directory, _ = create_staged_recovery(tmp_path)

    rollback_path = tmp_path / "auth_tracker.pre_recovery.db"
    rollback_path.write_bytes(b"existing rollback")

    with pytest.raises(
        RecoveryActivationError,
        match="rollback database already exists",
    ):
        resolve_recovery_activation_paths(
            database_path=database_path,
            restore_directory=restore_directory,
        )


def test_require_same_filesystem_accepts_matching_filesystems(
    tmp_path,
):
    first_path = tmp_path / "first.db"
    second_path = tmp_path / "second.db"

    first_path.touch()

    require_same_filesystem(
        first_path,
        second_path,
    )


def test_require_same_filesystem_rejects_different_filesystems(
    tmp_path,
):
    first_path = tmp_path / "first.db"
    second_path = tmp_path / "second.db"

    with patch(
        "authstatus_api.backups.recovery_activation._filesystem_identity",
        side_effect=[
            ("device", 1),
            ("device", 2),
        ],
    ):
        with pytest.raises(
            RecoveryActivationError,
            match="not on the same filesystem",
        ):
            require_same_filesystem(
                first_path,
                second_path,
            )


def test_find_database_sidecars_reports_existing_files(
    tmp_path,
):
    database_path = tmp_path / "auth_tracker.db"
    database_path.touch()

    wal_path = Path(f"{database_path.resolve()}-wal")
    shm_path = Path(f"{database_path.resolve()}-shm")

    wal_path.write_bytes(b"wal")
    shm_path.write_bytes(b"shm")

    assert find_database_sidecars(database_path) == [
        wal_path,
        shm_path,
    ]


def test_find_database_sidecars_does_not_modify_files(
    tmp_path,
):
    database_path = tmp_path / "auth_tracker.db"
    database_path.touch()

    journal_path = Path(f"{database_path.resolve()}-journal")
    journal_path.write_bytes(b"journal state")

    sidecars = find_database_sidecars(database_path)

    assert sidecars == [journal_path]
    assert journal_path.read_bytes() == b"journal state"


def test_verify_exclusive_database_access_accepts_idle_database():
    init_db()

    verify_exclusive_database_access()


def test_verify_exclusive_database_access_rejects_locked_database():
    init_db()

    settings = get_settings()
    database_path = Path(settings.database_path).resolve()

    locking_connection = sqlite3.connect(database_path)

    try:
        locking_connection.execute("BEGIN EXCLUSIVE")

        with pytest.raises(
            RecoveryActivationError,
            match="locked or in use",
        ):
            verify_exclusive_database_access()
    finally:
        locking_connection.execute("ROLLBACK")
        locking_connection.close()


def test_verify_api_port_available_accepts_refused_connection():
    with patch(
        "authstatus_api.backups.recovery_activation.socket.create_connection",
        side_effect=ConnectionRefusedError,
    ):
        verify_api_port_available(
            host="127.0.0.1",
            port=8000,
        )


def test_verify_api_port_available_rejects_listening_port():
    connection = patch(
        "authstatus_api.backups.recovery_activation.socket.create_connection"
    )

    with connection as mocked_connection:
        mocked_connection.return_value.__enter__.return_value = object()

        with pytest.raises(
            RecoveryActivationError,
            match="port 8000 is still in use",
        ):
            verify_api_port_available(
                host="127.0.0.1",
                port=8000,
            )


@pytest.mark.parametrize(
    "port",
    [
        0,
        65536,
    ],
)
def test_verify_api_port_available_rejects_invalid_port(
    port,
):
    with pytest.raises(
        RecoveryActivationError,
        match="API port must be between 1 and 65535",
    ):
        verify_api_port_available(
            port=port,
        )


def test_verify_managed_service_stopped_skips_when_not_configured():
    with patch(
        "authstatus_api.backups.recovery_activation.subprocess.run"
    ) as mocked_run:
        verify_managed_service_stopped(
            service_name=None,
        )

    mocked_run.assert_not_called()


def test_verify_windows_service_stopped():
    result = subprocess.CompletedProcess(
        args=["sc.exe", "query", "CareQueue"],
        returncode=0,
        stdout=(
            "SERVICE_NAME: CareQueue\n" "        STATE              : 1  STOPPED\n"
        ),
        stderr="",
    )

    with (
        patch(
            "authstatus_api.backups.recovery_activation.os.name",
            "nt",
        ),
        patch(
            "authstatus_api.backups.recovery_activation.subprocess.run",
            return_value=result,
        ),
    ):
        verify_managed_service_stopped(
            service_name="CareQueue",
        )


def test_verify_windows_service_rejects_running_service():
    result = subprocess.CompletedProcess(
        args=["sc.exe", "query", "CareQueue"],
        returncode=0,
        stdout=(
            "SERVICE_NAME: CareQueue\n" "        STATE              : 4  RUNNING\n"
        ),
        stderr="",
    )

    with (
        patch(
            "authstatus_api.backups.recovery_activation.os.name",
            "nt",
        ),
        patch(
            "authstatus_api.backups.recovery_activation.subprocess.run",
            return_value=result,
        ),
    ):
        with pytest.raises(
            RecoveryActivationError,
            match="service is not stopped",
        ):
            verify_managed_service_stopped(
                service_name="CareQueue",
            )


def test_verify_linux_service_accepts_inactive_service():
    result = subprocess.CompletedProcess(
        args=[
            "systemctl",
            "is-active",
            "carequeue.service",
        ],
        returncode=3,
        stdout="inactive\n",
        stderr="",
    )

    with (
        patch(
            "authstatus_api.backups.recovery_activation.platform.system",
            return_value="Linux",
        ),
        patch(
            "authstatus_api.backups.recovery_activation.subprocess.run",
            return_value=result,
        ),
    ):
        verify_managed_service_stopped(
            service_name="carequeue.service",
        )


def test_verify_linux_service_rejects_active_service():
    result = subprocess.CompletedProcess(
        args=[
            "systemctl",
            "is-active",
            "carequeue.service",
        ],
        returncode=0,
        stdout="active\n",
        stderr="",
    )

    with (
        patch(
            "authstatus_api.backups.recovery_activation.platform.system",
            return_value="Linux",
        ),
        patch(
            "authstatus_api.backups.recovery_activation.subprocess.run",
            return_value=result,
        ),
    ):
        with pytest.raises(
            RecoveryActivationError,
            match="service is not stopped",
        ):
            verify_managed_service_stopped(
                service_name="carequeue.service",
            )
