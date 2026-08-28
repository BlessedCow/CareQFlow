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
