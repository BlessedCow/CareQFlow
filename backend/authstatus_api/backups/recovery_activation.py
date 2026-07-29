from __future__ import annotations

import os
import platform
import socket
import subprocess
from pathlib import Path
from typing import TypedDict

from authstatus_api.backups.service import (
    BackupConfigError,
    BackupError,
    create_encrypted_database_backup,
    get_staged_database_recovery,
    verify_encrypted_database_backup,
)
from authstatus_api.persistence.connections import get_conn
from authstatus_api.persistence.paths import get_database_path
from authstatus_api.settings import get_settings, resolve_project_path


class RecoveryActivationError(RuntimeError):
    pass


class RecoveryActivationPaths(TypedDict):
    active_database: Path
    staged_database: Path
    rollback_database: Path


class RecoveryActivationPlan(TypedDict):
    active_database: Path
    staged_database: Path
    rollback_database: Path
    safety_backup: Path
    sidecars: list[Path]
    service_name: str | None
    api_host: str
    api_port: int


DATABASE_SIDECAR_SUFFIXES = (
    "-wal",
    "-shm",
    "-journal",
)


RECOVERY_CONFIRMATION_PHRASE = "ACTIVATE RECOVERY"


def _nearest_existing_path(path: Path) -> Path:
    current_path = path

    while not current_path.exists():
        if current_path.parent == current_path:
            raise RecoveryActivationError(
                "Unable to determine the database filesystem."
            )

        current_path = current_path.parent

    return current_path


def _filesystem_identity(path: Path) -> tuple[str, str | int]:
    existing_path = _nearest_existing_path(path.resolve())

    if os.name == "nt":
        drive = existing_path.drive.strip().lower()

        if not drive:
            raise RecoveryActivationError("Unable to determine the database volume.")

        return ("windows-drive", drive)

    return (
        "device",
        existing_path.stat().st_dev,
    )


def require_same_filesystem(
    *paths: Path,
) -> None:
    if not paths:
        raise RecoveryActivationError("No recovery paths were provided.")

    filesystem_identities = {_filesystem_identity(path) for path in paths}

    if len(filesystem_identities) != 1:
        raise RecoveryActivationError(
            "Recovery activation refused: the active database, "
            "staged database, and rollback destination are not "
            "on the same filesystem."
        )


def verify_managed_service_stopped(
    *,
    service_name: str | None,
) -> None:
    if service_name is None:
        return

    normalized_service_name = service_name.strip()

    if not normalized_service_name:
        raise RecoveryActivationError("The managed service name must not be empty.")

    operating_system = platform.system()

    if operating_system == "Windows":
        service_manager = "windows"
        command = [
            "sc.exe",
            "query",
            normalized_service_name,
        ]
    elif operating_system == "Linux":
        service_manager = "linux"
        command = [
            "systemctl",
            "is-active",
            normalized_service_name,
        ]
    else:
        raise RecoveryActivationError(
            "Managed service verification is not supported " "on this operating system."
        )

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        raise RecoveryActivationError(
            "Unable to verify the managed CareQueue service status."
        ) from exc

    combined_output = "\n".join(
        value
        for value in (
            result.stdout,
            result.stderr,
        )
        if value
    ).lower()

    if service_manager == "windows":
        if result.returncode != 0:
            raise RecoveryActivationError(
                "Unable to verify the managed CareQueue service status."
            )

        if "state" not in combined_output:
            raise RecoveryActivationError(
                "Unable to verify the managed CareQueue service status."
            )

        if "stopped" not in combined_output:
            raise RecoveryActivationError(
                "Recovery activation refused: the managed "
                "CareQueue service is not stopped."
            )

        return

    if result.returncode == 3 and "inactive" in combined_output:
        return

    if result.returncode == 0 and "inactive" in combined_output:
        return

    if "failed" in combined_output:
        return

    if "unknown" in combined_output or "not-found" in combined_output:
        raise RecoveryActivationError(
            "Unable to verify the managed CareQueue service status."
        )

    raise RecoveryActivationError(
        "Recovery activation refused: the managed " "CareQueue service is not stopped."
    )


def verify_api_port_available(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    timeout_seconds: float = 0.5,
) -> None:
    if not host.strip():
        raise RecoveryActivationError("The API host must not be empty.")

    if not 1 <= port <= 65535:
        raise RecoveryActivationError("The API port must be between 1 and 65535.")

    if timeout_seconds <= 0:
        raise RecoveryActivationError("The socket timeout must be greater than zero.")

    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout_seconds,
        ):
            pass
    except ConnectionRefusedError:
        return
    except TimeoutError as exc:
        raise RecoveryActivationError(
            "Unable to determine whether the CareQueue API " "port is available."
        ) from exc
    except OSError as exc:
        if getattr(exc, "winerror", None) == 10061:
            return

        raise RecoveryActivationError(
            "Unable to determine whether the CareQueue API " "port is available."
        ) from exc

    raise RecoveryActivationError(
        f"Recovery activation refused: port {port} is still in use."
    )


def resolve_recovery_activation_paths(
    *,
    database_path: Path | None = None,
    restore_directory: Path | None = None,
) -> RecoveryActivationPaths:
    settings = get_settings()
    active_database = (
        database_path.resolve()
        if database_path is not None
        else get_database_path().resolve()
    )
    destination_directory = resolve_project_path(
        restore_directory or settings.restore_directory
    )

    try:
        recovery_info = get_staged_database_recovery(
            restore_directory=destination_directory,
        )
    except BackupError as exc:
        raise RecoveryActivationError(
            "The pending database recovery is invalid."
        ) from exc

    if recovery_info is None:
        raise RecoveryActivationError("No database recovery is currently staged.")

    if not active_database.exists():
        raise RecoveryActivationError("The active database does not exist.")

    if not active_database.is_file():
        raise RecoveryActivationError("The active database path is not a file.")

    staged_database = (
        destination_directory / recovery_info["staged_filename"]
    ).resolve()

    rollback_database = active_database.with_name(
        f"{active_database.stem}.pre_recovery" f"{active_database.suffix}"
    )

    if rollback_database.exists():
        raise RecoveryActivationError("The recovery rollback database already exists.")

    require_same_filesystem(
        active_database,
        staged_database,
        rollback_database,
    )

    return {
        "active_database": active_database,
        "staged_database": staged_database,
        "rollback_database": rollback_database,
    }


def create_verified_active_database_backup(
    *,
    database_path: Path | None = None,
    backup_directory: Path | None = None,
) -> Path:
    settings = get_settings()
    active_database = (
        database_path.resolve()
        if database_path is not None
        else get_database_path().resolve()
    )
    destination_directory = resolve_project_path(
        backup_directory or settings.backup_directory
    )

    backup_path: Path | None = None

    try:
        backup_path = create_encrypted_database_backup(
            database_path=active_database,
            backup_directory=destination_directory,
        )
        verify_encrypted_database_backup(
            backup_path=backup_path,
        )
    except (
        BackupConfigError,
        BackupError,
    ) as exc:
        if backup_path is not None and backup_path.exists():
            try:
                backup_path.unlink()
            except OSError as cleanup_exc:
                raise RecoveryActivationError(
                    "The active database safety backup failed "
                    "verification and could not be removed."
                ) from cleanup_exc

        raise RecoveryActivationError(
            "Unable to create and verify an encrypted safety "
            "backup of the active database."
        ) from exc

    return backup_path


def prepare_recovery_activation(
    *,
    database_path: Path | None = None,
    backup_directory: Path | None = None,
    restore_directory: Path | None = None,
    service_name: str | None = None,
    api_host: str = "127.0.0.1",
    api_port: int = 8000,
) -> RecoveryActivationPlan:
    paths = resolve_recovery_activation_paths(
        database_path=database_path,
        restore_directory=restore_directory,
    )

    verify_managed_service_stopped(
        service_name=service_name,
    )
    verify_api_port_available(
        host=api_host,
        port=api_port,
    )
    verify_exclusive_database_access()

    sidecars = find_database_sidecars(
        paths["active_database"],
    )

    safety_backup = create_verified_active_database_backup(
        database_path=paths["active_database"],
        backup_directory=backup_directory,
    )

    return {
        "active_database": paths["active_database"],
        "staged_database": paths["staged_database"],
        "rollback_database": paths["rollback_database"],
        "safety_backup": safety_backup,
        "sidecars": sidecars,
        "service_name": service_name,
        "api_host": api_host,
        "api_port": api_port,
    }


def format_recovery_activation_plan(
    plan: RecoveryActivationPlan,
) -> str:
    service_display = plan["service_name"] or "Not configured"

    if plan["sidecars"]:
        sidecar_display = "\n".join(f"  - {sidecar}" for sidecar in plan["sidecars"])
    else:
        sidecar_display = "  None detected"

    return "\n".join(
        (
            "CareQueue Database Recovery Activation Plan",
            "",
            f"Active database:  {plan['active_database']}",
            f"Staged database:  {plan['staged_database']}",
            f"Rollback database: {plan['rollback_database']}",
            f"Safety backup:    {plan['safety_backup']}",
            f"Managed service:  {service_display}",
            f"API socket:       {plan['api_host']}:{plan['api_port']}",
            "",
            "Detected SQLite sidecars:",
            sidecar_display,
            "",
            "No database files have been replaced.",
            "The next operation will begin the atomic cutover.",
        )
    )


def require_recovery_activation_confirmation(
    confirmation: str,
) -> None:
    if confirmation != RECOVERY_CONFIRMATION_PHRASE:
        raise RecoveryActivationError(
            "Recovery activation canceled: the confirmation "
            "phrase did not match exactly."
        )


def find_database_sidecars(
    database_path: Path,
) -> list[Path]:
    resolved_database_path = database_path.resolve()

    return [
        Path(f"{resolved_database_path}{suffix}")
        for suffix in DATABASE_SIDECAR_SUFFIXES
        if Path(f"{resolved_database_path}{suffix}").exists()
    ]


def verify_exclusive_database_access() -> None:
    conn = None

    try:
        conn = get_conn()
        conn.execute("PRAGMA busy_timeout = 250")
        conn.execute("BEGIN EXCLUSIVE")
        conn.execute("ROLLBACK")
    except Exception as exc:
        if conn is not None:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass

        raise RecoveryActivationError(
            "Recovery activation refused: the active database " "is locked or in use."
        ) from exc
    finally:
        if conn is not None:
            conn.close()
