from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

WINDOWS_INSTALLER_WRAPPER = (
    PROJECT_ROOT / "deployment" / "windows" / "installer" / "invoke-install.ps1"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _powershell_function(content: str, name: str) -> str:
    marker = f"function {name} {{"

    assert marker in content

    remainder = content.split(marker, maxsplit=1)[1]

    depth = 1
    index = 0

    while index < len(remainder):
        character = remainder[index]

        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1

            if depth == 0:
                return remainder[:index]

        index += 1

    raise AssertionError(f"PowerShell function was not closed: {name}")


def test_windows_upgrade_has_version_validation_helpers():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    assert "function Test-CareQueueVersion {" in content
    assert "function Compare-CareQueueVersions {" in content
    assert "function Get-CareQueueInstalledVersion {" in content
    assert "function Assert-CareQueueUpgradeVersion {" in content


def test_windows_upgrade_rejects_same_version_and_downgrade():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Assert-CareQueueUpgradeVersion",
    )

    assert "Use Repair instead of Upgrade." in function
    assert "CareQueue downgrade refused:" in function
    assert "Compare-CareQueueVersions" in function


def test_windows_upgrade_allows_legacy_install_without_version_metadata():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Assert-CareQueueUpgradeVersion",
    )

    assert "Installed CareQueue version metadata is unavailable." in function
    assert "Continuing legacy upgrade validation." in function


def test_windows_upgrade_reads_version_from_payload_metadata():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    assert (
        "$incomingVersion = "
        "[string]$payloadMetadata.application.backend_version" in content
    )

    assert "Test-CareQueueVersion -Version $incomingVersion" in content


def test_windows_upgrade_validation_runs_before_installer_logging():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    validation_index = content.index("Assert-CareQueueUpgradeVersion")

    logging_index = content.index('$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"')

    assert validation_index < logging_index


def test_windows_upgrade_reads_install_state_as_json():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Get-CareQueueInstalledVersion",
    )

    assert "ConvertFrom-Json" in function
    assert "installed_version" in function
    assert "Invoke-Expression" not in function


WINDOWS_PRODUCTION_INSTALLER = (
    PROJECT_ROOT / "deployment" / "windows" / "install-production.ps1"
)


def test_windows_production_installer_requires_release_version():
    content = _read(WINDOWS_PRODUCTION_INSTALLER)

    assert '[ValidatePattern("^\\d+\\.\\d+\\.\\d+$")]' in content
    assert "[string]$ReleaseVersion" in content


def test_windows_installer_passes_payload_version_to_production_install():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    assert '"-ReleaseVersion",' in content
    assert "$incomingVersion," in content


def test_windows_production_installer_writes_install_state():
    content = _read(WINDOWS_PRODUCTION_INSTALLER)

    assert '"install-state.json"' in content
    assert "schema_version" in content
    assert "installed_version" in content
    assert "package_platform" in content
    assert "application_origin" in content
    assert "$ReleaseVersion" in content


def test_windows_install_state_is_written_atomically():
    content = _read(WINDOWS_PRODUCTION_INSTALLER)

    assert '$temporaryInstallStatePath = "$installStatePath.tmp"' in content
    assert "ConvertTo-Json" in content
    assert "Move-Item" in content
    assert "-Destination $installStatePath" in content


def test_windows_install_state_written_after_backend_validation():
    content = _read(WINDOWS_PRODUCTION_INSTALLER)

    validation_index = content.index("CareQueue production backend validated.")
    state_index = content.index("Writing CareQueue installation state...")

    assert validation_index < state_index
