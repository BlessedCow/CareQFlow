from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
INSTALLER_WRAPPER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "invoke-install.sh"
)

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or shutil.which("bash") is None,
    reason="Linux installer runtime tests require Linux and Bash.",
)


def _installer_without_main(tmp_path: Path) -> Path:
    content = INSTALLER_WRAPPER.read_text(encoding="utf-8")

    assert content.rstrip().endswith('main "$@"')

    content = content.rsplit('main "$@"', maxsplit=1)[0]

    script_path = tmp_path / "invoke-install-functions.sh"
    script_path.write_text(content, encoding="utf-8")

    return script_path


def _run_bash(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("left_version", "right_version", "expected"),
    [
        ("0.3.1", "0.3.0", "1"),
        ("0.3.0", "0.3.1", "-1"),
        ("0.3.0", "0.3.0", "0"),
        ("0.10.0", "0.9.0", "1"),
        ("1.0.0", "0.99.99", "1"),
        ("1.10.0", "1.9.99", "1"),
        ("10.0.0", "2.99.99", "1"),
    ],
)
def test_compare_versions_uses_numeric_semantic_ordering(
    tmp_path: Path,
    left_version: str,
    right_version: str,
    expected: str,
):
    installer = _installer_without_main(tmp_path)

    result = _run_bash(f"""
        source "{installer}"
        compare_versions "{left_version}" "{right_version}"
        """)

    assert result.returncode == 0
    assert result.stdout.strip() == expected


@pytest.mark.parametrize(
    "version",
    [
        "0.3.0",
        "1.0.0",
        "10.25.300",
    ],
)
def test_validate_version_string_accepts_supported_versions(
    tmp_path: Path,
    version: str,
):
    installer = _installer_without_main(tmp_path)

    result = _run_bash(f"""
        source "{installer}"
        validate_version_string "{version}"
        """)

    assert result.returncode == 0


@pytest.mark.parametrize(
    "version",
    [
        "",
        "1",
        "1.0",
        "v1.0.0",
        "1.0.0-beta",
        "1.0.0.0",
        "1.a.0",
    ],
)
def test_validate_version_string_rejects_unsupported_versions(
    tmp_path: Path,
    version: str,
):
    installer = _installer_without_main(tmp_path)

    result = _run_bash(f"""
        source "{installer}"
        validate_version_string "{version}"
        """)

    assert result.returncode != 0


def test_upgrade_accepts_newer_release(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    release_metadata = tmp_path / "carequeue-release.env"
    install_state = tmp_path / "install-state.env"

    release_metadata.write_text(
        "CAREQUEUE_APP_VERSION=0.4.0\n",
        encoding="utf-8",
    )
    install_state.write_text(
        "CAREQUEUE_INSTALLED_VERSION=0.3.0\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"
        MODE="upgrade"
        RELEASE_METADATA_FILE="{release_metadata}"
        INSTALL_STATE_FILE="{install_state}"
        validate_upgrade_version
        """)

    assert result.returncode == 0
    assert "Validated CareQueue upgrade path: 0.3.0 -> 0.4.0" in result.stdout


def test_upgrade_rejects_same_release(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    release_metadata = tmp_path / "carequeue-release.env"
    install_state = tmp_path / "install-state.env"

    release_metadata.write_text(
        "CAREQUEUE_APP_VERSION=0.3.0\n",
        encoding="utf-8",
    )
    install_state.write_text(
        "CAREQUEUE_INSTALLED_VERSION=0.3.0\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"
        MODE="upgrade"
        RELEASE_METADATA_FILE="{release_metadata}"
        INSTALL_STATE_FILE="{install_state}"
        validate_upgrade_version
        """)

    assert result.returncode != 0
    assert "Use repair instead of upgrade." in result.stderr


def test_upgrade_rejects_downgrade(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    release_metadata = tmp_path / "carequeue-release.env"
    install_state = tmp_path / "install-state.env"

    release_metadata.write_text(
        "CAREQUEUE_APP_VERSION=0.3.0\n",
        encoding="utf-8",
    )
    install_state.write_text(
        "CAREQUEUE_INSTALLED_VERSION=0.4.0\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"
        MODE="upgrade"
        RELEASE_METADATA_FILE="{release_metadata}"
        INSTALL_STATE_FILE="{install_state}"
        validate_upgrade_version
        """)

    assert result.returncode != 0
    assert "CareQueue downgrade refused:" in result.stderr


def test_upgrade_allows_legacy_install_without_state_metadata(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    release_metadata = tmp_path / "carequeue-release.env"
    missing_install_state = tmp_path / "missing-install-state.env"

    release_metadata.write_text(
        "CAREQUEUE_APP_VERSION=0.4.0\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"
        MODE="upgrade"
        RELEASE_METADATA_FILE="{release_metadata}"
        INSTALL_STATE_FILE="{missing_install_state}"
        validate_upgrade_version
        """)

    assert result.returncode == 0
    assert "Installed CareQueue version metadata is unavailable." in result.stdout
    assert "Continuing legacy upgrade validation." in result.stdout


def test_upgrade_rejects_invalid_incoming_version(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    release_metadata = tmp_path / "carequeue-release.env"
    install_state = tmp_path / "install-state.env"

    release_metadata.write_text(
        "CAREQUEUE_APP_VERSION=0.4.0-beta\n",
        encoding="utf-8",
    )
    install_state.write_text(
        "CAREQUEUE_INSTALLED_VERSION=0.3.0\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"
        MODE="upgrade"
        RELEASE_METADATA_FILE="{release_metadata}"
        INSTALL_STATE_FILE="{install_state}"
        validate_upgrade_version
        """)

    assert result.returncode != 0
    assert (
        "Incoming CareQueue package has an invalid application version:"
        in result.stderr
    )


def test_upgrade_rejects_invalid_installed_version(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    release_metadata = tmp_path / "carequeue-release.env"
    install_state = tmp_path / "install-state.env"

    release_metadata.write_text(
        "CAREQUEUE_APP_VERSION=0.4.0\n",
        encoding="utf-8",
    )
    install_state.write_text(
        "CAREQUEUE_INSTALLED_VERSION=not-a-version\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"
        MODE="upgrade"
        RELEASE_METADATA_FILE="{release_metadata}"
        INSTALL_STATE_FILE="{install_state}"
        validate_upgrade_version
        """)

    assert result.returncode != 0
    assert "Installed CareQueue version metadata is invalid:" in result.stderr


def test_upgrade_recovery_record_is_created_with_expected_state(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    backup_path = tmp_path / "pre-upgrade.db.enc"
    log_path = tmp_path / "upgrade.log"

    backup_path.write_bytes(b"verified-backup")
    log_path.write_text("installer log\n", encoding="utf-8")

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        INSTALLED_VERSION="0.3.0"
        INCOMING_VERSION="0.4.0"
        PRE_UPGRADE_BACKUP_PATH="{backup_path}"
        LOG_PATH="{log_path}"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        write_upgrade_recovery_record

        printf 'RECORD=%s\\n' "${{UPGRADE_RECOVERY_RECORD}}"
        cat "${{UPGRADE_RECOVERY_RECORD}}"
        """)

    assert result.returncode == 0

    expected_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"

    assert expected_record.is_file()

    record = expected_record.read_text(encoding="utf-8")

    assert "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1" in record
    assert "CAREQUEUE_PREVIOUS_VERSION=0.3.0" in record
    assert "CAREQUEUE_INCOMING_VERSION=0.4.0" in record
    assert f"CAREQUEUE_PRE_UPGRADE_BACKUP={backup_path}" in record
    assert f"CAREQUEUE_INSTALLER_LOG={log_path}" in record
    assert "CAREQUEUE_UPGRADE_ATTEMPTED_AT=" in record
    assert "CAREQUEUE_UPGRADE_STATUS=pending" in record


def test_upgrade_recovery_record_rejects_missing_verified_backup(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        INSTALLED_VERSION="0.3.0"
        INCOMING_VERSION="0.4.0"
        PRE_UPGRADE_BACKUP_PATH=""
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        write_upgrade_recovery_record
        """)

    assert result.returncode != 0
    assert (
        "Cannot create upgrade recovery state because the "
        "verified pre-upgrade backup path is unavailable." in result.stderr
    )
    assert not recovery_directory.exists()


def test_upgrade_recovery_status_can_be_marked_completed(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_record = tmp_path / "upgrade.env"

    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                "CAREQUEUE_UPGRADE_STATUS=pending",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        UPGRADE_RECOVERY_RECORD="{recovery_record}"

        update_upgrade_recovery_status "completed"
        """)

    assert result.returncode == 0

    record = recovery_record.read_text(encoding="utf-8")

    assert "CAREQUEUE_UPGRADE_STATUS=completed" in record
    assert "CAREQUEUE_UPGRADE_STATUS=pending" not in record
    assert not Path(f"{recovery_record}.tmp").exists()


def test_upgrade_recovery_status_can_be_marked_failed(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_record = tmp_path / "upgrade.env"

    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                "CAREQUEUE_UPGRADE_STATUS=pending",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        UPGRADE_RECOVERY_RECORD="{recovery_record}"

        update_upgrade_recovery_status "failed"
        """)

    assert result.returncode == 0

    record = recovery_record.read_text(encoding="utf-8")

    assert "CAREQUEUE_UPGRADE_STATUS=failed" in record
    assert "CAREQUEUE_UPGRADE_STATUS=pending" not in record
    assert not Path(f"{recovery_record}.tmp").exists()


def test_rollback_selects_latest_failed_upgrade_record(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    recovery_directory.mkdir()

    backup_old = tmp_path / "backup-old.db.enc"
    backup_new = tmp_path / "backup-new.db.enc"

    backup_old.write_bytes(b"old")
    backup_new.write_bytes(b"new")

    application_old = tmp_path / "application-old.tar.gz"
    application_new = tmp_path / "application-new.tar.gz"

    application_old.write_bytes(b"old application")
    application_new.write_bytes(b"new application")

    application_old_checksum = subprocess.run(
        ["sha256sum", str(application_old)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[0]

    application_new_checksum = subprocess.run(
        ["sha256sum", str(application_new)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[0]

    completed_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"
    failed_old_record = recovery_directory / "upgrade-0.4.0-to-0.5.0.env"
    failed_new_record = recovery_directory / "upgrade-0.5.0-to-0.6.0.env"

    completed_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={backup_old}",
                "CAREQUEUE_UPGRADE_STATUS=completed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    failed_old_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.4.0",
                "CAREQUEUE_INCOMING_VERSION=0.5.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={backup_old}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION={application_old}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256={application_old_checksum}",
                "CAREQUEUE_UPGRADE_STATUS=failed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    failed_new_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.5.0",
                "CAREQUEUE_INCOMING_VERSION=0.6.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={backup_new}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION={application_new}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256={application_new_checksum}",
                "CAREQUEUE_UPGRADE_STATUS=failed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    subprocess.run(
        ["touch", "-d", "3 minutes ago", str(completed_record)],
        check=True,
    )
    subprocess.run(
        ["touch", "-d", "2 minutes ago", str(failed_old_record)],
        check=True,
    )
    subprocess.run(
        ["touch", "-d", "1 minute ago", str(failed_new_record)],
        check=True,
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        resolve_failed_upgrade_recovery_record

        printf 'RECORD=%s\\n' "${{ROLLBACK_RECOVERY_RECORD}}"
        printf 'PREVIOUS=%s\\n' "${{ROLLBACK_PREVIOUS_VERSION}}"
        printf 'INCOMING=%s\\n' "${{ROLLBACK_INCOMING_VERSION}}"
        printf 'BACKUP=%s\\n' "${{ROLLBACK_BACKUP_PATH}}"
        """)

    assert result.returncode == 0
    assert f"RECORD={failed_new_record}" in result.stdout
    assert "PREVIOUS=0.5.0" in result.stdout
    assert "INCOMING=0.6.0" in result.stdout
    assert f"BACKUP={backup_new}" in result.stdout


def test_rollback_rejects_when_no_failed_upgrade_record_exists(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    recovery_directory.mkdir()

    completed_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"
    backup_path = tmp_path / "backup.db.enc"

    backup_path.write_bytes(b"backup")

    completed_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={backup_path}",
                "CAREQUEUE_UPGRADE_STATUS=completed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        resolve_failed_upgrade_recovery_record
        """)

    assert result.returncode != 0
    assert "No failed CareQueue upgrade recovery record was found." in result.stderr


def test_rollback_rejects_missing_backup_file(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    recovery_directory.mkdir()

    missing_backup = tmp_path / "missing.db.enc"
    failed_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"

    failed_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={missing_backup}",
                "CAREQUEUE_UPGRADE_STATUS=failed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        resolve_failed_upgrade_recovery_record
        """)

    assert result.returncode != 0
    assert (
        f"The pre-upgrade rollback backup does not exist: {missing_backup}"
        in result.stderr
    )


def test_rollback_rejects_empty_backup_file(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    recovery_directory.mkdir()

    empty_backup = tmp_path / "empty.db.enc"
    empty_backup.touch()

    failed_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"

    failed_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={empty_backup}",
                "CAREQUEUE_UPGRADE_STATUS=failed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        resolve_failed_upgrade_recovery_record
        """)

    assert result.returncode != 0
    assert f"The pre-upgrade rollback backup is empty: {empty_backup}" in result.stderr


def test_rollback_recovery_status_can_be_marked_staged(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_record = tmp_path / "upgrade.env"

    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                "CAREQUEUE_UPGRADE_STATUS=failed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"

        update_rollback_recovery_status "rollback_staged"
        """)

    assert result.returncode == 0

    record = recovery_record.read_text(encoding="utf-8")

    assert "CAREQUEUE_UPGRADE_STATUS=rollback_staged" in record
    assert "CAREQUEUE_UPGRADE_STATUS=failed" not in record
    assert not Path(f"{recovery_record}.tmp").exists()


def test_rollback_resolver_does_not_reselect_staged_record(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    recovery_directory.mkdir()

    backup_path = tmp_path / "backup.db.enc"
    backup_path.write_bytes(b"backup")

    staged_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"

    staged_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={backup_path}",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        resolve_failed_upgrade_recovery_record
        """)

    assert result.returncode != 0
    assert "No failed CareQueue upgrade recovery record was found." in result.stderr


def test_rollback_activation_stops_api_before_recovery_and_restarts_after_success(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    backend_directory = install_directory / "backend"
    scripts_directory = backend_directory / "scripts"
    venv_bin_directory = backend_directory / ".venv" / "bin"
    config_directory = tmp_path / "config"
    data_directory = tmp_path / "data"
    backup_directory = tmp_path / "backups"
    fake_bin_directory = tmp_path / "bin"
    command_log = tmp_path / "commands.log"

    scripts_directory.mkdir(parents=True)
    venv_bin_directory.mkdir(parents=True)
    config_directory.mkdir()
    data_directory.mkdir()
    backup_directory.mkdir()
    fake_bin_directory.mkdir()

    activation_script = scripts_directory / "activate_staged_recovery.py"
    activation_script.write_text("# test\n", encoding="utf-8")

    python_path = venv_bin_directory / "python"
    python_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_path.chmod(0o755)

    systemctl = fake_bin_directory / "systemctl"
    systemctl.write_text(
        f"""#!/bin/sh
printf 'systemctl %s\\n' "$*" >> "{command_log}"
exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    systemd_run = fake_bin_directory / "systemd-run"
    systemd_run.write_text(
        f"""#!/bin/sh
printf 'systemd-run %s\\n' "$*" >> "{command_log}"
exit 0
""",
        encoding="utf-8",
    )
    systemd_run.chmod(0o755)

    curl = fake_bin_directory / "curl"
    curl.write_text(
        """#!/bin/sh
    exit 0
    """,
        encoding="utf-8",
    )
    curl.chmod(0o755)

    sleep = fake_bin_directory / "sleep"
    sleep.write_text(
        """#!/bin/sh
    exit 0
    """,
        encoding="utf-8",
    )
    sleep.chmod(0o755)

    install_state = config_directory / "install-state.env"
    install_state.write_text(
        "CAREQUEUE_APPLICATION_ORIGIN=https://careqflow.local\n",
        encoding="utf-8",
    )

    recovery_record = tmp_path / "upgrade.env"
    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        export PATH="{fake_bin_directory}:$PATH"

        source "{installer}"

        MODE="rollback"
        INSTALL_DIRECTORY="{install_directory}"
        CONFIG_DIRECTORY="{config_directory}"
        INSTALL_STATE_FILE="{install_state}"
        DATA_DIRECTORY="{data_directory}"
        BACKUP_DIRECTORY="{backup_directory}"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"

        activate_failed_upgrade_rollback
        """)

    assert result.returncode == 0

    commands = command_log.read_text(encoding="utf-8").splitlines()

    stop_index = commands.index("systemctl stop carequeue-api.service")
    activation_index = next(
        index
        for index, command in enumerate(commands)
        if command.startswith("systemd-run ")
    )
    start_index = commands.index("systemctl start carequeue-api.service")

    assert stop_index < activation_index < start_index

    record = recovery_record.read_text(encoding="utf-8")
    assert "CAREQUEUE_UPGRADE_STATUS=rollback_completed" in record
    assert "CAREQUEUE_UPGRADE_STATUS=rollback_activated" not in record

    assert "Rollback database activation completed." in result.stdout
    assert "CareQueue services started after rollback activation." in result.stdout

    assert "Upgrade recovery status: rollback_completed" in result.stdout

    assert "systemctl start carequeue-caddy.service" in commands
    assert "systemctl enable --now carequeue-backup.timer" in commands
    assert "systemctl is-active --quiet carequeue-api.service" in commands
    assert "systemctl is-active --quiet carequeue-caddy.service" in commands
    assert "systemctl is-active --quiet carequeue-backup.timer" in commands


def test_rollback_activation_failure_keeps_api_stopped_and_status_staged(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    backend_directory = install_directory / "backend"
    scripts_directory = backend_directory / "scripts"
    venv_bin_directory = backend_directory / ".venv" / "bin"
    config_directory = tmp_path / "config"
    data_directory = tmp_path / "data"
    backup_directory = tmp_path / "backups"
    fake_bin_directory = tmp_path / "bin"
    command_log = tmp_path / "commands.log"

    scripts_directory.mkdir(parents=True)
    venv_bin_directory.mkdir(parents=True)
    config_directory.mkdir()
    data_directory.mkdir()
    backup_directory.mkdir()
    fake_bin_directory.mkdir()

    activation_script = scripts_directory / "activate_staged_recovery.py"
    activation_script.write_text("# test\n", encoding="utf-8")

    python_path = venv_bin_directory / "python"
    python_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_path.chmod(0o755)

    systemctl = fake_bin_directory / "systemctl"
    systemctl.write_text(
        f"""#!/bin/sh
printf 'systemctl %s\\n' "$*" >> "{command_log}"
exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    systemd_run = fake_bin_directory / "systemd-run"
    systemd_run.write_text(
        f"""#!/bin/sh
printf 'systemd-run %s\\n' "$*" >> "{command_log}"
exit 1
""",
        encoding="utf-8",
    )
    systemd_run.chmod(0o755)

    recovery_record = tmp_path / "upgrade.env"
    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        export PATH="{fake_bin_directory}:$PATH"

        source "{installer}"

        MODE="rollback"
        INSTALL_DIRECTORY="{install_directory}"
        CONFIG_DIRECTORY="{config_directory}"
        DATA_DIRECTORY="{data_directory}"
        BACKUP_DIRECTORY="{backup_directory}"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"

        activate_failed_upgrade_rollback
        """)

    assert result.returncode != 0

    commands = command_log.read_text(encoding="utf-8").splitlines()

    assert "systemctl stop carequeue-api.service" in commands
    assert not any(
        command == "systemctl start carequeue-api.service" for command in commands
    )

    record = recovery_record.read_text(encoding="utf-8")
    assert "CAREQUEUE_UPGRADE_STATUS=rollback_staged" in record
    assert "CAREQUEUE_UPGRADE_STATUS=rollback_activated" not in record

    assert "CareQueue API remains stopped for safety." in result.stdout


def test_rollback_activation_does_not_mark_success_when_api_restart_fails(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    backend_directory = install_directory / "backend"
    scripts_directory = backend_directory / "scripts"
    venv_bin_directory = backend_directory / ".venv" / "bin"
    config_directory = tmp_path / "config"
    data_directory = tmp_path / "data"
    backup_directory = tmp_path / "backups"
    fake_bin_directory = tmp_path / "bin"
    command_log = tmp_path / "commands.log"

    scripts_directory.mkdir(parents=True)
    venv_bin_directory.mkdir(parents=True)
    config_directory.mkdir()
    data_directory.mkdir()
    backup_directory.mkdir()
    fake_bin_directory.mkdir()

    activation_script = scripts_directory / "activate_staged_recovery.py"
    activation_script.write_text("# test\n", encoding="utf-8")

    python_path = venv_bin_directory / "python"
    python_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_path.chmod(0o755)

    systemctl = fake_bin_directory / "systemctl"
    systemctl.write_text(
        f"""#!/bin/sh
printf 'systemctl %s\\n' "$*" >> "{command_log}"

if [ "$1" = "start" ]; then
    exit 1
fi

exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    systemd_run = fake_bin_directory / "systemd-run"
    systemd_run.write_text(
        f"""#!/bin/sh
printf 'systemd-run %s\\n' "$*" >> "{command_log}"
exit 0
""",
        encoding="utf-8",
    )
    systemd_run.chmod(0o755)

    recovery_record = tmp_path / "upgrade.env"
    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        export PATH="{fake_bin_directory}:$PATH"

        source "{installer}"

        MODE="rollback"
        INSTALL_DIRECTORY="{install_directory}"
        CONFIG_DIRECTORY="{config_directory}"
        DATA_DIRECTORY="{data_directory}"
        BACKUP_DIRECTORY="{backup_directory}"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"

        activate_failed_upgrade_rollback
        """)

    assert result.returncode != 0

    record = recovery_record.read_text(encoding="utf-8")

    assert "CAREQUEUE_UPGRADE_STATUS=rollback_activated" in record
    assert (
        "Rollback activation completed, but carequeue-api.service could not be started."
        in result.stderr
    )


def test_rollback_restores_previous_installed_version(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_state = tmp_path / "install-state.env"

    install_state.write_text(
        "\n".join(
            [
                "CAREQUEUE_INSTALL_STATE_SCHEMA=1",
                "CAREQUEUE_INSTALLED_VERSION=0.4.0",
                "CAREQUEUE_PACKAGE_PLATFORM=linux",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        ROLLBACK_PREVIOUS_VERSION="0.3.0"
        INSTALL_STATE_FILE="{install_state}"

        restore_previous_install_state_version
        """)

    assert result.returncode == 0

    state = install_state.read_text(encoding="utf-8")

    assert "CAREQUEUE_INSTALLED_VERSION=0.3.0" in state
    assert "CAREQUEUE_INSTALLED_VERSION=0.4.0" not in state
    assert "CAREQUEUE_PACKAGE_PLATFORM=linux" in state
    assert not Path(f"{install_state}.tmp").exists()


def test_rollback_adds_version_to_legacy_install_state(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_state = tmp_path / "install-state.env"

    install_state.write_text(
        "\n".join(
            [
                "CAREQUEUE_INSTALL_DIRECTORY=/opt/carequeue",
                "CAREQUEUE_PACKAGE_PLATFORM=linux",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        ROLLBACK_PREVIOUS_VERSION="0.3.0"
        INSTALL_STATE_FILE="{install_state}"

        restore_previous_install_state_version
        """)

    assert result.returncode == 0

    state = install_state.read_text(encoding="utf-8")

    assert state.count("CAREQUEUE_INSTALLED_VERSION=0.3.0") == 1
    assert "CAREQUEUE_INSTALL_DIRECTORY=/opt/carequeue" in state


def test_rollback_rejects_invalid_previous_version_metadata(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_state = tmp_path / "install-state.env"
    install_state.write_text(
        "CAREQUEUE_INSTALLED_VERSION=0.4.0\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        ROLLBACK_PREVIOUS_VERSION="invalid"
        INSTALL_STATE_FILE="{install_state}"

        restore_previous_install_state_version
        """)

    assert result.returncode != 0
    assert (
        "Cannot restore installed version metadata because the previous "
        "CareQueue version is invalid:" in result.stderr
    )

    assert (
        install_state.read_text(encoding="utf-8")
        == "CAREQUEUE_INSTALLED_VERSION=0.4.0\n"
    )


def test_pre_upgrade_application_archive_preserves_expected_payload(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    backend_directory = install_directory / "backend"
    frontend_directory = install_directory / "frontend"
    deployment_directory = install_directory / "deployment"
    venv_directory = backend_directory / ".venv"
    recovery_directory = tmp_path / "recovery"

    backend_directory.mkdir(parents=True)
    frontend_directory.mkdir()
    deployment_directory.mkdir()
    venv_directory.mkdir()

    (backend_directory / "backend.txt").write_text(
        "backend\n",
        encoding="utf-8",
    )
    (frontend_directory / "frontend.txt").write_text(
        "frontend\n",
        encoding="utf-8",
    )
    (deployment_directory / "deployment.txt").write_text(
        "deployment\n",
        encoding="utf-8",
    )
    (venv_directory / "should-not-be-archived.txt").write_text(
        "venv\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        INSTALLED_VERSION="0.3.0"
        INSTALL_DIRECTORY="{install_directory}"
        UPGRADE_APPLICATION_RECOVERY_DIRECTORY="{recovery_directory}"

        create_verified_pre_upgrade_application_archive

        printf 'ARCHIVE=%s\\n' "${{PRE_UPGRADE_APPLICATION_ARCHIVE}}"
        printf 'SHA256=%s\\n' "${{PRE_UPGRADE_APPLICATION_SHA256}}"
        """)

    assert result.returncode == 0

    archive_path = recovery_directory / "carequeue-application-0.3.0.tar.gz"

    checksum_path = Path(f"{archive_path}.sha256")

    assert archive_path.is_file()
    assert archive_path.stat().st_size > 0
    assert checksum_path.is_file()

    archive_listing = subprocess.run(
        ["tar", "-tzf", str(archive_path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert "backend/backend.txt" in archive_listing
    assert "frontend/frontend.txt" in archive_listing
    assert "deployment/deployment.txt" in archive_listing
    assert "backend/.venv" not in archive_listing

    checksum = checksum_path.read_text(
        encoding="utf-8",
    ).split()[0]

    assert len(checksum) == 64
    assert checksum in result.stdout


def test_pre_upgrade_application_archive_rejects_invalid_installed_version(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    backend_directory = install_directory / "backend"
    frontend_directory = install_directory / "frontend"
    deployment_directory = install_directory / "deployment"

    backend_directory.mkdir(parents=True)
    frontend_directory.mkdir()
    deployment_directory.mkdir()

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        INSTALLED_VERSION="invalid"
        INSTALL_DIRECTORY="{install_directory}"
        UPGRADE_APPLICATION_RECOVERY_DIRECTORY="{tmp_path / "recovery"}"

        create_verified_pre_upgrade_application_archive
        """)

    assert result.returncode != 0
    assert (
        "Cannot preserve the installed application because its "
        "version metadata is invalid:" in result.stderr
    )


def test_pre_upgrade_application_archive_rejects_missing_application_tree(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    install_directory.mkdir()

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        INSTALLED_VERSION="0.3.0"
        INSTALL_DIRECTORY="{install_directory}"
        UPGRADE_APPLICATION_RECOVERY_DIRECTORY="{tmp_path / "recovery"}"

        create_verified_pre_upgrade_application_archive
        """)

    assert result.returncode != 0
    assert (
        "Cannot preserve the installed CareQueue application because "
        "required application directories are missing." in result.stderr
    )


def test_pre_upgrade_application_archive_legacy_upgrade_skips_payload(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        INSTALLED_VERSION=""
        INSTALL_DIRECTORY="{tmp_path / "install"}"
        UPGRADE_APPLICATION_RECOVERY_DIRECTORY="{tmp_path / "recovery"}"

        create_verified_pre_upgrade_application_archive
        """)

    assert result.returncode == 0
    assert (
        "application rollback payload will not be created for this legacy upgrade"
        in result.stdout
    )
    assert not (tmp_path / "recovery").exists()


def test_rollback_accepts_verified_application_archive(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    recovery_directory.mkdir()

    database_backup = tmp_path / "database.db.enc"
    application_archive = tmp_path / "application.tar.gz"

    database_backup.write_bytes(b"database-backup")
    application_archive.write_bytes(b"application-backup")

    checksum = subprocess.run(
        ["sha256sum", str(application_archive)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[0]

    recovery_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"

    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={database_backup}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION={application_archive}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256={checksum}",
                "CAREQUEUE_UPGRADE_STATUS=failed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        resolve_failed_upgrade_recovery_record
        """)

    assert result.returncode == 0
    assert f"Pre-upgrade application: {application_archive}" in result.stdout
    assert f"Verified application SHA256: {checksum}" in result.stdout


def test_rollback_rejects_application_archive_checksum_mismatch(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    recovery_directory.mkdir()

    database_backup = tmp_path / "database.db.enc"
    application_archive = tmp_path / "application.tar.gz"

    database_backup.write_bytes(b"database-backup")
    application_archive.write_bytes(b"tampered-application")

    recovery_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"

    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={database_backup}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION={application_archive}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256={'0' * 64}",
                "CAREQUEUE_UPGRADE_STATUS=failed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        resolve_failed_upgrade_recovery_record
        """)

    assert result.returncode != 0
    assert (
        "Pre-upgrade application archive checksum verification failed." in result.stderr
    )


def test_rollback_rejects_invalid_application_checksum_metadata(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_directory = tmp_path / "recovery"
    recovery_directory.mkdir()

    database_backup = tmp_path / "database.db.enc"
    application_archive = tmp_path / "application.tar.gz"

    database_backup.write_bytes(b"database-backup")
    application_archive.write_bytes(b"application-backup")

    recovery_record = recovery_directory / "upgrade-0.3.0-to-0.4.0.env"

    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_PREVIOUS_VERSION=0.3.0",
                "CAREQUEUE_INCOMING_VERSION=0.4.0",
                f"CAREQUEUE_PRE_UPGRADE_BACKUP={database_backup}",
                f"CAREQUEUE_PRE_UPGRADE_APPLICATION={application_archive}",
                "CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256=invalid",
                "CAREQUEUE_UPGRADE_STATUS=failed",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        UPGRADE_RECOVERY_DIRECTORY="{recovery_directory}"

        resolve_failed_upgrade_recovery_record
        """)

    assert result.returncode != 0
    assert (
        "The failed upgrade recovery record contains an invalid "
        "application archive checksum." in result.stderr
    )


def test_rollback_application_staging_extracts_expected_payload(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    source_directory = tmp_path / "source"
    backend_directory = source_directory / "backend"
    frontend_directory = source_directory / "frontend"
    deployment_directory = source_directory / "deployment"

    backend_directory.mkdir(parents=True)
    frontend_directory.mkdir()
    deployment_directory.mkdir()

    (backend_directory / "backend.txt").write_text(
        "backend\n",
        encoding="utf-8",
    )
    (frontend_directory / "frontend.txt").write_text(
        "frontend\n",
        encoding="utf-8",
    )
    (deployment_directory / "deployment.txt").write_text(
        "deployment\n",
        encoding="utf-8",
    )

    archive_path = tmp_path / "application.tar.gz"

    subprocess.run(
        [
            "tar",
            "-czf",
            str(archive_path),
            "-C",
            str(source_directory),
            "backend",
            "frontend",
            "deployment",
        ],
        check=True,
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        DATA_DIRECTORY="{tmp_path / "data"}"
        ROLLBACK_APPLICATION_ARCHIVE="{archive_path}"

        stage_verified_rollback_application

        printf 'STAGED=%s\\n' "${{ROLLBACK_APPLICATION_STAGING_ROOT}}"
        """)

    assert result.returncode == 0

    staged_line = next(
        line for line in result.stdout.splitlines() if line.startswith("STAGED=")
    )
    staged_root = Path(staged_line.removeprefix("STAGED="))

    assert (staged_root / "backend" / "backend.txt").is_file()
    assert (staged_root / "frontend" / "frontend.txt").is_file()
    assert (staged_root / "deployment" / "deployment.txt").is_file()


def test_rollback_application_staging_rejects_missing_required_tree(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    source_directory = tmp_path / "source"
    backend_directory = source_directory / "backend"
    frontend_directory = source_directory / "frontend"

    backend_directory.mkdir(parents=True)
    frontend_directory.mkdir()

    archive_path = tmp_path / "application.tar.gz"

    subprocess.run(
        [
            "tar",
            "-czf",
            str(archive_path),
            "-C",
            str(source_directory),
            "backend",
            "frontend",
        ],
        check=True,
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        DATA_DIRECTORY="{tmp_path / "data"}"
        ROLLBACK_APPLICATION_ARCHIVE="{archive_path}"

        stage_verified_rollback_application
        """)

    assert result.returncode != 0
    assert (
        "The staged rollback application payload is missing required "
        "application directories." in result.stderr
    )


def test_rollback_application_staging_rejects_virtual_environment(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    source_directory = tmp_path / "source"
    backend_directory = source_directory / "backend"
    frontend_directory = source_directory / "frontend"
    deployment_directory = source_directory / "deployment"
    venv_directory = backend_directory / ".venv"

    backend_directory.mkdir(parents=True)
    frontend_directory.mkdir()
    deployment_directory.mkdir()
    venv_directory.mkdir()

    archive_path = tmp_path / "application.tar.gz"

    subprocess.run(
        [
            "tar",
            "-czf",
            str(archive_path),
            "-C",
            str(source_directory),
            "backend",
            "frontend",
            "deployment",
        ],
        check=True,
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        DATA_DIRECTORY="{tmp_path / "data"}"
        ROLLBACK_APPLICATION_ARCHIVE="{archive_path}"

        stage_verified_rollback_application
        """)

    assert result.returncode != 0
    assert (
        "The rollback application payload unexpectedly contains a "
        "Python virtual environment." in result.stderr
    )


def test_rollback_preserves_failed_application_payload(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    backend_directory = install_directory / "backend"
    frontend_directory = install_directory / "frontend"
    deployment_directory = install_directory / "deployment"
    venv_directory = backend_directory / ".venv"
    recovery_directory = tmp_path / "recovery"

    backend_directory.mkdir(parents=True)
    frontend_directory.mkdir()
    deployment_directory.mkdir()
    venv_directory.mkdir()

    (backend_directory / "failed-backend.txt").write_text(
        "failed backend\n",
        encoding="utf-8",
    )
    (frontend_directory / "failed-frontend.txt").write_text(
        "failed frontend\n",
        encoding="utf-8",
    )
    (deployment_directory / "failed-deployment.txt").write_text(
        "failed deployment\n",
        encoding="utf-8",
    )
    (venv_directory / "excluded.txt").write_text(
        "venv\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        INSTALL_DIRECTORY="{install_directory}"
        ROLLBACK_INCOMING_VERSION="0.4.0"
        UPGRADE_APPLICATION_RECOVERY_DIRECTORY="{recovery_directory}"

        preserve_failed_application_before_rollback

        printf 'ARCHIVE=%s\\n' "${{FAILED_APPLICATION_ARCHIVE}}"
        printf 'SHA256=%s\\n' "${{FAILED_APPLICATION_SHA256}}"
        """)

    assert result.returncode == 0

    archive_path = recovery_directory / "carequeue-failed-application-0.4.0.tar.gz"

    assert archive_path.is_file()
    assert archive_path.stat().st_size > 0
    assert Path(f"{archive_path}.sha256").is_file()

    archive_listing = subprocess.run(
        ["tar", "-tzf", str(archive_path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert "backend/failed-backend.txt" in archive_listing
    assert "frontend/failed-frontend.txt" in archive_listing
    assert "deployment/failed-deployment.txt" in archive_listing
    assert "backend/.venv" not in archive_listing


def test_rollback_records_failed_application_metadata(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_record = tmp_path / "upgrade.env"
    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    failed_archive = tmp_path / "failed.tar.gz"

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"
        FAILED_APPLICATION_ARCHIVE="{failed_archive}"
        FAILED_APPLICATION_SHA256="{'a' * 64}"

        record_failed_application_for_rollback
        """)

    assert result.returncode == 0

    record = recovery_record.read_text(encoding="utf-8")

    assert f"CAREQUEUE_FAILED_APPLICATION={failed_archive}" in record
    assert f"CAREQUEUE_FAILED_APPLICATION_SHA256={'a' * 64}" in record
    assert not Path(f"{recovery_record}.tmp").exists()


def test_rollback_failed_application_metadata_is_not_duplicated(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    recovery_record = tmp_path / "upgrade.env"

    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_FAILED_APPLICATION=/old/archive.tar.gz",
                f"CAREQUEUE_FAILED_APPLICATION_SHA256={'0' * 64}",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    failed_archive = tmp_path / "new.tar.gz"

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"
        FAILED_APPLICATION_ARCHIVE="{failed_archive}"
        FAILED_APPLICATION_SHA256="{'b' * 64}"

        record_failed_application_for_rollback
        """)

    assert result.returncode == 0

    record = recovery_record.read_text(encoding="utf-8")

    assert record.count("CAREQUEUE_FAILED_APPLICATION=") == 1
    assert record.count("CAREQUEUE_FAILED_APPLICATION_SHA256=") == 1
    assert f"CAREQUEUE_FAILED_APPLICATION={failed_archive}" in record


def test_rollback_application_swap_restores_previous_payload_and_rebuilds_venv(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    staged_directory = tmp_path / "staged"
    recovery_staging = tmp_path / "data" / "recovery" / "application-staging"
    fake_bin = tmp_path / "bin"
    command_log = tmp_path / "commands.log"

    for directory in (
        install_directory / "backend",
        install_directory / "frontend",
        install_directory / "deployment",
        staged_directory / "backend",
        staged_directory / "frontend",
        staged_directory / "deployment",
        recovery_staging,
        fake_bin,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    (install_directory / "backend" / "failed.txt").write_text(
        "failed backend\n",
        encoding="utf-8",
    )
    (install_directory / "frontend" / "failed.txt").write_text(
        "failed frontend\n",
        encoding="utf-8",
    )
    (install_directory / "deployment" / "failed.txt").write_text(
        "failed deployment\n",
        encoding="utf-8",
    )

    (staged_directory / "backend" / "previous.txt").write_text(
        "previous backend\n",
        encoding="utf-8",
    )
    (staged_directory / "frontend" / "previous.txt").write_text(
        "previous frontend\n",
        encoding="utf-8",
    )
    (staged_directory / "deployment" / "previous.txt").write_text(
        "previous deployment\n",
        encoding="utf-8",
    )
    (staged_directory / "backend" / "requirements.txt").write_text(
        "example-package==1.0\n",
        encoding="utf-8",
    )

    systemctl = fake_bin / "systemctl"
    systemctl.write_text(
        f"""#!/bin/sh
printf 'systemctl %s\\n' "$*" >> "{command_log}"
exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    python3 = fake_bin / "python3"
    python3.write_text(
        f"""#!/bin/sh
printf 'python3 %s\\n' "$*" >> "{command_log}"

if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
    venv_path="$3"
    mkdir -p "$venv_path/bin"

    cat > "$venv_path/bin/python" <<'EOF'
#!/bin/sh
printf 'venv-python %s\\n' "$*" >> "{command_log}"
exit 0
EOF

    chmod +x "$venv_path/bin/python"
    exit 0
fi

exit 1
""",
        encoding="utf-8",
    )
    python3.chmod(0o755)

    result = _run_bash(f"""
        export PATH="{fake_bin}:$PATH"

        source "{installer}"

        MODE="rollback"
        INSTALL_DIRECTORY="{install_directory}"
        DATA_DIRECTORY="{tmp_path / "data"}"
        ROLLBACK_APPLICATION_STAGING_ROOT="{staged_directory}"

        replace_failed_application_with_rollback_payload

        printf 'FAILED_STAGING=%s\\n' \
            "${{FAILED_APPLICATION_STAGING_DIRECTORY}}"
        """)

    assert result.returncode == 0

    assert not (install_directory / "backend" / "failed.txt").exists()
    assert not (install_directory / "frontend" / "failed.txt").exists()
    assert not (install_directory / "deployment" / "failed.txt").exists()

    assert (install_directory / "backend" / "previous.txt").is_file()
    assert (install_directory / "frontend" / "previous.txt").is_file()
    assert (install_directory / "deployment" / "previous.txt").is_file()

    assert (install_directory / "backend" / ".venv" / "bin" / "python").is_file()

    staged_line = next(
        line
        for line in result.stdout.splitlines()
        if line.startswith("FAILED_STAGING=")
    )
    failed_staging = Path(staged_line.removeprefix("FAILED_STAGING="))

    assert (failed_staging / "backend" / "failed.txt").is_file()
    assert (failed_staging / "frontend" / "failed.txt").is_file()
    assert (failed_staging / "deployment" / "failed.txt").is_file()

    commands = command_log.read_text(encoding="utf-8")

    assert "systemctl stop carequeue-api.service" in commands
    assert "systemctl stop carequeue-caddy.service" in commands
    assert "python3 -m venv" in commands
    assert "venv-python -m pip install --upgrade pip setuptools wheel" in commands
    assert "venv-python -m pip install --requirement" in commands
    assert "venv-python -c import authstatus_api.main" in commands


def test_rollback_application_swap_does_not_move_files_when_api_stop_fails(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    staged_directory = tmp_path / "staged"
    fake_bin = tmp_path / "bin"

    for directory in (
        install_directory / "backend",
        install_directory / "frontend",
        install_directory / "deployment",
        staged_directory / "backend",
        staged_directory / "frontend",
        staged_directory / "deployment",
        fake_bin,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    failed_backend = install_directory / "backend" / "failed.txt"
    failed_backend.write_text(
        "failed backend\n",
        encoding="utf-8",
    )

    systemctl = fake_bin / "systemctl"
    systemctl.write_text(
        """#!/bin/sh
if [ "$1" = "stop" ] && [ "$2" = "carequeue-api.service" ]; then
    exit 1
fi

exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    result = _run_bash(f"""
        export PATH="{fake_bin}:$PATH"

        source "{installer}"

        MODE="rollback"
        INSTALL_DIRECTORY="{install_directory}"
        DATA_DIRECTORY="{tmp_path / "data"}"
        ROLLBACK_APPLICATION_STAGING_ROOT="{staged_directory}"

        replace_failed_application_with_rollback_payload
        """)

    assert result.returncode != 0

    assert failed_backend.is_file()
    assert (install_directory / "frontend").is_dir()
    assert (install_directory / "deployment").is_dir()

    assert (
        "CareQueue rollback could not stop carequeue-api.service "
        "before application replacement." in result.stderr
    )


def test_rollback_application_swap_does_not_move_files_when_caddy_stop_fails(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    staged_directory = tmp_path / "staged"
    fake_bin = tmp_path / "bin"

    for directory in (
        install_directory / "backend",
        install_directory / "frontend",
        install_directory / "deployment",
        staged_directory / "backend",
        staged_directory / "frontend",
        staged_directory / "deployment",
        fake_bin,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    failed_backend = install_directory / "backend" / "failed.txt"
    failed_backend.write_text(
        "failed backend\n",
        encoding="utf-8",
    )

    systemctl = fake_bin / "systemctl"
    systemctl.write_text(
        """#!/bin/sh
if [ "$1" = "stop" ] && [ "$2" = "carequeue-caddy.service" ]; then
    exit 1
fi

exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    result = _run_bash(f"""
        export PATH="{fake_bin}:$PATH"

        source "{installer}"

        MODE="rollback"
        INSTALL_DIRECTORY="{install_directory}"
        DATA_DIRECTORY="{tmp_path / "data"}"
        ROLLBACK_APPLICATION_STAGING_ROOT="{staged_directory}"

        replace_failed_application_with_rollback_payload
        """)

    assert result.returncode != 0

    assert failed_backend.is_file()
    assert (install_directory / "frontend").is_dir()
    assert (install_directory / "deployment").is_dir()

    assert (
        "CareQueue rollback could not stop carequeue-caddy.service "
        "before application replacement." in result.stderr
    )


def test_rollback_restores_failed_application_when_backend_copy_fails(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    staged_directory = tmp_path / "staged"
    recovery_staging = tmp_path / "data" / "recovery" / "application-staging"
    fake_bin = tmp_path / "bin"

    for directory in (
        install_directory / "backend",
        install_directory / "frontend",
        install_directory / "deployment",
        staged_directory / "backend",
        staged_directory / "frontend",
        staged_directory / "deployment",
        recovery_staging,
        fake_bin,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    (install_directory / "backend" / "failed.txt").write_text(
        "failed backend\n",
        encoding="utf-8",
    )
    (install_directory / "frontend" / "failed.txt").write_text(
        "failed frontend\n",
        encoding="utf-8",
    )
    (install_directory / "deployment" / "failed.txt").write_text(
        "failed deployment\n",
        encoding="utf-8",
    )

    (staged_directory / "backend" / "previous.txt").write_text(
        "previous backend\n",
        encoding="utf-8",
    )
    (staged_directory / "frontend" / "previous.txt").write_text(
        "previous frontend\n",
        encoding="utf-8",
    )
    (staged_directory / "deployment" / "previous.txt").write_text(
        "previous deployment\n",
        encoding="utf-8",
    )

    systemctl = fake_bin / "systemctl"
    systemctl.write_text(
        """#!/bin/sh
exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    cp = fake_bin / "cp"
    cp.write_text(
        """#!/bin/sh
case "$*" in
    *"/staged/backend"*"/install/backend"*)
        exit 1
        ;;
esac

exec /bin/cp "$@"
""",
        encoding="utf-8",
    )
    cp.chmod(0o755)

    recovery_record = tmp_path / "upgrade.env"
    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        export PATH="{fake_bin}:$PATH"

        source "{installer}"

        MODE="rollback"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"
        INSTALL_DIRECTORY="{install_directory}"
        DATA_DIRECTORY="{tmp_path / "data"}"
        ROLLBACK_APPLICATION_STAGING_ROOT="{staged_directory}"

        replace_failed_application_with_rollback_payload
        """)

    assert result.returncode != 0

    assert (install_directory / "backend" / "failed.txt").is_file()
    assert (install_directory / "frontend" / "failed.txt").is_file()
    assert (install_directory / "deployment" / "failed.txt").is_file()

    assert not (install_directory / "backend" / "previous.txt").exists()
    assert not (install_directory / "frontend" / "previous.txt").exists()
    assert not (install_directory / "deployment" / "previous.txt").exists()

    assert (
        "The failed application was restored and CareQueue services remain stopped."
        in result.stderr
    )

    record = recovery_record.read_text(encoding="utf-8")

    assert "CAREQUEUE_UPGRADE_STATUS=rollback_application_restored" in record


def test_rollback_restores_failed_application_when_venv_creation_fails(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    staged_directory = tmp_path / "staged"
    recovery_staging = tmp_path / "data" / "recovery" / "application-staging"
    fake_bin = tmp_path / "bin"

    for directory in (
        install_directory / "backend",
        install_directory / "frontend",
        install_directory / "deployment",
        staged_directory / "backend",
        staged_directory / "frontend",
        staged_directory / "deployment",
        recovery_staging,
        fake_bin,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    (install_directory / "backend" / "failed.txt").write_text(
        "failed backend\n",
        encoding="utf-8",
    )
    (install_directory / "frontend" / "failed.txt").write_text(
        "failed frontend\n",
        encoding="utf-8",
    )
    (install_directory / "deployment" / "failed.txt").write_text(
        "failed deployment\n",
        encoding="utf-8",
    )

    (staged_directory / "backend" / "previous.txt").write_text(
        "previous backend\n",
        encoding="utf-8",
    )
    (staged_directory / "frontend" / "previous.txt").write_text(
        "previous frontend\n",
        encoding="utf-8",
    )
    (staged_directory / "deployment" / "previous.txt").write_text(
        "previous deployment\n",
        encoding="utf-8",
    )
    (staged_directory / "backend" / "requirements.txt").write_text(
        "example-package==1.0\n",
        encoding="utf-8",
    )

    systemctl = fake_bin / "systemctl"
    systemctl.write_text(
        """#!/bin/sh
exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    python3 = fake_bin / "python3"
    python3.write_text(
        """#!/bin/sh
exit 1
""",
        encoding="utf-8",
    )
    python3.chmod(0o755)

    recovery_record = tmp_path / "upgrade.env"
    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        export PATH="{fake_bin}:$PATH"

        source "{installer}"

        MODE="rollback"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"
        INSTALL_DIRECTORY="{install_directory}"
        DATA_DIRECTORY="{tmp_path / "data"}"
        ROLLBACK_APPLICATION_STAGING_ROOT="{staged_directory}"

        replace_failed_application_with_rollback_payload
        """)

    assert result.returncode != 0

    assert (install_directory / "backend" / "failed.txt").is_file()
    assert (install_directory / "frontend" / "failed.txt").is_file()
    assert (install_directory / "deployment" / "failed.txt").is_file()

    assert not (install_directory / "backend" / "previous.txt").exists()
    assert not (install_directory / "frontend" / "previous.txt").exists()
    assert not (install_directory / "deployment" / "previous.txt").exists()

    assert (
        "Failed to rebuild the previous CareQueue Python environment. "
        "The failed application was restored and CareQueue services remain stopped."
        in result.stderr
    )

    record = recovery_record.read_text(encoding="utf-8")

    assert "CAREQUEUE_UPGRADE_STATUS=rollback_application_restored" in record


def test_failed_application_restore_helper_restores_all_application_trees(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    install_directory = tmp_path / "install"
    failed_staging = tmp_path / "failed-staging"

    for directory in (
        install_directory / "backend",
        install_directory / "frontend",
        install_directory / "deployment",
        failed_staging / "backend",
        failed_staging / "frontend",
        failed_staging / "deployment",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    (install_directory / "backend" / "partial.txt").write_text(
        "partial rollback\n",
        encoding="utf-8",
    )

    (failed_staging / "backend" / "failed.txt").write_text(
        "failed backend\n",
        encoding="utf-8",
    )
    (failed_staging / "frontend" / "failed.txt").write_text(
        "failed frontend\n",
        encoding="utf-8",
    )
    (failed_staging / "deployment" / "failed.txt").write_text(
        "failed deployment\n",
        encoding="utf-8",
    )

    recovery_record = tmp_path / "upgrade.env"
    recovery_record.write_text(
        "\n".join(
            [
                "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1",
                "CAREQUEUE_UPGRADE_STATUS=rollback_staged",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"
        INSTALL_DIRECTORY="{install_directory}"
        FAILED_APPLICATION_STAGING_DIRECTORY="{failed_staging}"
        RECOVERY_RECORD="{recovery_record}"

        restore_failed_application_after_swap_failure
        """)

    assert result.returncode == 0

    assert (install_directory / "backend" / "failed.txt").is_file()
    assert (install_directory / "frontend" / "failed.txt").is_file()
    assert (install_directory / "deployment" / "failed.txt").is_file()
    assert not (install_directory / "backend" / "partial.txt").exists()

    assert (
        "Failed application restored after rollback replacement failure."
        in result.stdout
    )

    record = recovery_record.read_text(encoding="utf-8")

    assert "CAREQUEUE_UPGRADE_STATUS=rollback_application_restored" in record
    assert "CAREQUEUE_UPGRADE_STATUS=rollback_staged" not in record

    assert (
        "CareQueue services remain stopped pending administrator review."
        in result.stdout
    )


def test_successful_rollback_cleanup_removes_only_temporary_staging(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    rollback_staging = tmp_path / "rollback-staging"
    failed_staging = tmp_path / "failed-staging"

    rollback_staging.mkdir()
    failed_staging.mkdir()

    (rollback_staging / "temporary.txt").write_text(
        "temporary rollback data\n",
        encoding="utf-8",
    )
    (failed_staging / "temporary.txt").write_text(
        "temporary failed app\n",
        encoding="utf-8",
    )

    database_backup = tmp_path / "backup.db.enc"
    previous_archive = tmp_path / "previous.tar.gz"
    failed_archive = tmp_path / "failed.tar.gz"
    recovery_record = tmp_path / "upgrade.env"

    database_backup.write_bytes(b"database")
    previous_archive.write_bytes(b"previous")
    failed_archive.write_bytes(b"failed")
    recovery_record.write_text(
        "CAREQUEUE_UPGRADE_STATUS=rollback_completed\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="rollback"
        ROLLBACK_APPLICATION_STAGING_DIRECTORY="{rollback_staging}"
        ROLLBACK_APPLICATION_STAGING_ROOT="{rollback_staging}"
        FAILED_APPLICATION_STAGING_DIRECTORY="{failed_staging}"

        ROLLBACK_BACKUP_PATH="{database_backup}"
        ROLLBACK_APPLICATION_ARCHIVE="{previous_archive}"
        FAILED_APPLICATION_ARCHIVE="{failed_archive}"
        ROLLBACK_RECOVERY_RECORD="{recovery_record}"

        cleanup_successful_rollback_staging
        """)

    assert result.returncode == 0

    assert not rollback_staging.exists()
    assert not failed_staging.exists()

    assert database_backup.is_file()
    assert previous_archive.is_file()
    assert failed_archive.is_file()
    assert recovery_record.is_file()

    assert (
        "Temporary rollback application staging directories removed." in result.stdout
    )


def test_post_rollback_health_failure_does_not_mark_rollback_completed(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    install_state = tmp_path / "install-state.env"
    install_state.write_text(
        "\n".join(
            [
                "CAREQUEUE_APPLICATION_ORIGIN=https://careqflow.local",
                "",
            ]
        ),
        encoding="utf-8",
    )

    curl = fake_bin / "curl"
    curl.write_text(
        """#!/bin/sh
exit 1
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)

    sleep = fake_bin / "sleep"
    sleep.write_text(
        """#!/bin/sh
exit 0
""",
        encoding="utf-8",
    )
    sleep.chmod(0o755)

    result = _run_bash(f"""
        export PATH="{fake_bin}:$PATH"

        source "{installer}"

        MODE="rollback"
        INSTALL_STATE_FILE="{install_state}"

        validate_post_rollback_health
        """)

    assert result.returncode != 0
    assert (
        "CareQueue did not pass health and readiness checks after rollback."
        in result.stderr
    )
    assert "rollback was not marked complete." in result.stderr


def test_post_rollback_service_validation_rejects_inactive_service(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    systemctl = fake_bin / "systemctl"
    systemctl.write_text(
        """#!/bin/sh
if [ "$1" = "is-active" ] \
    && [ "$3" = "carequeue-caddy.service" ]; then
    exit 1
fi

exit 0
""",
        encoding="utf-8",
    )
    systemctl.chmod(0o755)

    result = _run_bash(f"""
        export PATH="{fake_bin}:$PATH"

        source "{installer}"

        MODE="rollback"

        validate_post_rollback_services
        """)

    assert result.returncode != 0
    assert "carequeue-caddy.service is not active." in result.stderr


def test_license_acceptance_accepts_explicit_accept(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    license_notice = tmp_path / "LICENSE"
    license_notice.write_text(
        "CareQueue test license\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="install"
        LICENSE_NOTICE_FILE="{license_notice}"

        printf 'ACCEPT\\n' | require_license_acceptance
        """)

    assert result.returncode == 0
    assert "CareQueue License Agreement" in result.stdout
    assert "CareQueue test license" in result.stdout
    assert "CareQueue license terms accepted." in result.stdout


def test_license_acceptance_rejects_non_accept_response(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    license_notice = tmp_path / "LICENSE"
    license_notice.write_text(
        "CareQueue test license\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="upgrade"
        LICENSE_NOTICE_FILE="{license_notice}"

        printf 'NO\\n' | require_license_acceptance
        """)

    assert result.returncode != 0
    assert "CareQueue License Agreement" in result.stdout
    assert "License terms were not accepted." in result.stdout


def test_license_acceptance_rejects_missing_input(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    license_notice = tmp_path / "LICENSE"
    license_notice.write_text(
        "CareQueue test license\n",
        encoding="utf-8",
    )

    result = _run_bash(f"""
        source "{installer}"

        MODE="install"
        LICENSE_NOTICE_FILE="{license_notice}"

        require_license_acceptance < /dev/null
        """)

    assert result.returncode != 0
    assert "License acceptance was not provided." in result.stderr


def test_license_acceptance_rejects_missing_license_notice(
    tmp_path: Path,
):
    installer = _installer_without_main(tmp_path)

    missing_license = tmp_path / "missing-LICENSE"

    result = _run_bash(f"""
        source "{installer}"

        MODE="install"
        LICENSE_NOTICE_FILE="{missing_license}"

        printf 'ACCEPT\\n' | require_license_acceptance
        """)

    assert result.returncode != 0
    assert "CareQueue license notice was not found:" in result.stderr


@pytest.mark.parametrize(
    "mode",
    [
        "repair",
        "rollback",
        "uninstall",
    ],
)
def test_license_acceptance_is_skipped_for_existing_install_operations(
    tmp_path: Path,
    mode: str,
):
    installer = _installer_without_main(tmp_path)

    missing_license = tmp_path / "missing-LICENSE"

    result = _run_bash(f"""
        source "{installer}"

        MODE="{mode}"
        LICENSE_NOTICE_FILE="{missing_license}"

        require_license_acceptance < /dev/null
        """)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
