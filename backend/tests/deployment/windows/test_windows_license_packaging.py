from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

WINDOWS_PAYLOAD_BUILDER = (
    PROJECT_ROOT / "deployment" / "windows" / "installer" / "build-payload.ps1"
)
WINDOWS_PRODUCTION_INSTALLER = (
    PROJECT_ROOT / "deployment" / "windows" / "install-production.ps1"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_windows_payload_builder_requires_repository_license_files():
    content = _read(WINDOWS_PAYLOAD_BUILDER)

    assert "$licenseNoticePath = Join-Path" in content
    assert "$licenseTextsDirectory = Join-Path" in content
    assert '"LICENSE"' in content
    assert '"BUSL-1.1.txt"' in content
    assert '"MIT.txt"' in content

    required_sources_index = content.index("$requiredSourcePaths = @(")
    payload_assembly_index = content.index(
        'Write-Status "Assembling CareQFlow application files..."'
    )

    required_sources = content[required_sources_index:payload_assembly_index]

    assert "$licenseNoticePath" in required_sources
    assert 'Join-Path $licenseTextsDirectory "BUSL-1.1.txt"' in required_sources
    assert 'Join-Path $licenseTextsDirectory "MIT.txt"' in required_sources


def test_windows_payload_builder_copies_and_validates_license_files():
    content = _read(WINDOWS_PAYLOAD_BUILDER)

    assert "$payloadLicenseTextsDirectory = Join-Path" in content
    assert '"LICENSES"' in content

    deployment_copy_index = content.index('Join-Path $deploymentSourceDirectory "*"')
    payload_validation_index = content.index(
        'Write-Status "Validating the assembled payload..."'
    )

    licensing_copy = content[deployment_copy_index:payload_validation_index]

    assert "$licenseNoticePath" in licensing_copy
    assert "$payloadLicenseTextsDirectory" in licensing_copy
    assert 'Join-Path $licenseTextsDirectory "*"' in licensing_copy

    required_payload_index = content.index("$payloadRequiredPaths = @(")
    runtime_validation_index = content.index("$payloadPythonExecutable = Join-Path")

    required_payload = content[required_payload_index:runtime_validation_index]

    assert 'Join-Path $resolvedOutputDirectory "LICENSE"' in required_payload
    assert '"BUSL-1.1.txt"' in required_payload
    assert '"MIT.txt"' in required_payload


def test_windows_payload_metadata_describes_license_paths():
    content = _read(WINDOWS_PAYLOAD_BUILDER)

    assert "license_notice" in content
    assert '"LICENSE"' in content
    assert "license_texts" in content
    assert '"LICENSES"' in content


def test_windows_payload_manifest_covers_packaged_license_files():
    content = _read(WINDOWS_PAYLOAD_BUILDER)

    license_copy_index = content.index("-Destination $payloadLicenseTextsDirectory")
    manifest_enumeration_index = content.index("$payloadManifestFiles = @(")

    assert license_copy_index < manifest_enumeration_index
    assert (
        "-Recurse"
        in content[
            manifest_enumeration_index : content.index(
                "$payloadManifestLines = foreach",
                manifest_enumeration_index,
            )
        ]
    )


def test_windows_production_installer_requires_and_installs_license_files():
    content = _read(WINDOWS_PRODUCTION_INSTALLER)

    required_sources_index = content.index("$requiredSourcePaths = @(")
    required_sources_end = content.index(
        ")",
        required_sources_index,
    )
    required_sources = content[required_sources_index:required_sources_end]

    assert '"LICENSE"' in required_sources
    assert '"LICENSES\\BUSL-1.1.txt"' in required_sources
    assert '"LICENSES\\MIT.txt"' in required_sources

    assert "$stagingLicenseNoticePath = Join-Path" in content
    assert "$stagingLicenseTextsDirectory = Join-Path" in content
    assert "$installedLicenseNoticePath = Join-Path" in content
    assert "$installedLicenseTextsDirectory = Join-Path" in content

    assert "$installedLicenseTextsDirectory," in content
    assert "-LiteralPath $stagingLicenseNoticePath" in content
    assert "-LiteralPath $stagingLicenseTextsDirectory" in content
    assert "-Destination $InstallDirectory" in content


def test_windows_production_installer_replaces_license_notice_only_with_force():
    content = _read(WINDOWS_PRODUCTION_INSTALLER)

    installed_license_index = content.index("$installedLicenseNoticePath = Join-Path")
    installed_copy_index = content.index("-LiteralPath $stagingLicenseNoticePath")

    replacement = content[installed_license_index:installed_copy_index]

    assert "Test-Path" in replacement
    assert "$installedLicenseNoticePath" in replacement
    assert "if (-not $Force)" in replacement
    assert "Remove-Item" in replacement
