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
