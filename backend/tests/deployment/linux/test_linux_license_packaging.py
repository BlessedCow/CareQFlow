from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

LINUX_PACKAGE_BUILDER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "build-payload.ps1"
)

LINUX_INSTALLER_WRAPPER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "invoke-install.sh"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _shell_function(content: str, name: str) -> str:
    marker = f"{name}() {{"

    assert marker in content

    return content.split(marker, maxsplit=1)[1].split(
        "\n}",
        maxsplit=1,
    )[0]


def test_linux_package_builder_requires_license_files():
    content = _read(LINUX_PACKAGE_BUILDER)

    required_paths = content.split(
        "$requiredPaths = @(",
        maxsplit=1,
    )[1].split(
        ")",
        maxsplit=1,
    )[0]

    assert '"LICENSE"' in required_paths
    assert '"LICENSES\\BUSL-1.1.txt"' in required_paths
    assert '"LICENSES\\MIT.txt"' in required_paths


def test_linux_package_builder_copies_license_files():
    content = _read(LINUX_PACKAGE_BUILDER)

    assert "$licenseNoticeDestination = Join-Path" in content
    assert "$licenseTextsDestination = Join-Path" in content

    assert 'Join-Path $repositoryRoot "LICENSE"' in content
    assert 'Join-Path $repositoryRoot "LICENSES"' in content

    assert "-Destination $licenseNoticeDestination" in content
    assert "-Destination $stagingDirectory" in content


def test_linux_release_metadata_describes_license_paths():
    content = _read(LINUX_PACKAGE_BUILDER)

    assert '"CAREQUEUE_LICENSE_NOTICE=LICENSE"' in content
    assert '"CAREQUEUE_LICENSE_TEXTS=LICENSES"' in content


def test_linux_installer_uses_packaged_license_notice():
    content = _read(LINUX_INSTALLER_WRAPPER)

    assert 'LICENSE_NOTICE_FILE="${PACKAGE_ROOT_DIRECTORY}/LICENSE"' in content


def test_linux_license_acceptance_applies_only_to_install_and_upgrade():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "require_license_acceptance",
    )

    assert '"${MODE}" != "install"' in function
    assert '"${MODE}" != "upgrade"' in function

    assert "repair" not in function
    assert "rollback" not in function
    assert "uninstall" not in function


def test_linux_license_acceptance_requires_explicit_accept():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "require_license_acceptance",
    )

    assert 'cat "${LICENSE_NOTICE_FILE}"' in function
    assert "Type ACCEPT to agree and continue:" in function
    assert "ACCEPT)" in function
    assert "License terms were not accepted." in function
    assert "exit 1" in function


def test_linux_license_acceptance_happens_before_system_changes():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    license_index = main_function.index(
        "require_license_acceptance",
    )
    logging_index = main_function.index(
        "prepare_logging",
    )
    backup_index = main_function.index(
        "create_verified_pre_upgrade_backup",
    )
    operation_index = main_function.index(
        'case "${MODE}" in',
    )

    assert license_index < logging_index
    assert license_index < backup_index
    assert license_index < operation_index


def test_linux_production_installer_requires_packaged_license_files():
    content = _read(PROJECT_ROOT / "deployment" / "linux" / "install-production.sh")

    assert '"${SOURCE_DIRECTORY}/LICENSE"' in content
    assert '"${SOURCE_DIRECTORY}/LICENSES/BUSL-1.1.txt"' in content
    assert '"${SOURCE_DIRECTORY}/LICENSES/MIT.txt"' in content


def test_linux_production_installer_installs_license_files():
    content = _read(PROJECT_ROOT / "deployment" / "linux" / "install-production.sh")

    assert '"${INSTALL_DIRECTORY}/LICENSE"' in content
    assert '"${INSTALL_DIRECTORY}/LICENSES"' in content

    assert (
        '"${SOURCE_DIRECTORY}/LICENSE" \\\n'
        '        "${INSTALL_DIRECTORY}/LICENSE"' in content
    )

    assert (
        '"${SOURCE_DIRECTORY}/LICENSES/." \\\n'
        '        "${INSTALL_DIRECTORY}/LICENSES/"' in content
    )


def test_linux_production_installer_replaces_stale_license_material():
    content = _read(PROJECT_ROOT / "deployment" / "linux" / "install-production.sh")

    copy_function = _shell_function(
        content,
        "copy_application_files",
    )

    assert '"${INSTALL_DIRECTORY}/LICENSE"' in copy_function
    assert '"${INSTALL_DIRECTORY}/LICENSES"' in copy_function
    assert "rm -rf" in copy_function


def test_linux_upgrade_archive_preserves_license_material_when_present():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "create_verified_pre_upgrade_application_archive",
    )

    assert "application_archive_paths+=(LICENSE)" in function
    assert "application_archive_paths+=(LICENSES)" in function
    assert '"${application_archive_paths[@]}"' in function


def test_linux_failed_application_archive_preserves_license_material():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "preserve_failed_application_before_rollback",
    )

    assert "application_archive_paths+=(LICENSE)" in function
    assert "application_archive_paths+=(LICENSES)" in function
    assert '"${application_archive_paths[@]}"' in function


def test_linux_rollback_moves_failed_license_material_aside():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "replace_failed_application_with_rollback_payload",
    )

    assert '"${INSTALL_DIRECTORY}/LICENSE"' in function
    assert '"${FAILED_APPLICATION_STAGING_DIRECTORY}/LICENSE"' in function
    assert '"${INSTALL_DIRECTORY}/LICENSES"' in function
    assert '"${FAILED_APPLICATION_STAGING_DIRECTORY}/LICENSES"' in function


def test_linux_rollback_restores_previous_license_material_when_available():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "replace_failed_application_with_rollback_payload",
    )

    assert '"${ROLLBACK_APPLICATION_STAGING_ROOT}/LICENSE"' in function
    assert '"${ROLLBACK_APPLICATION_STAGING_ROOT}/LICENSES"' in function

    assert '"${INSTALL_DIRECTORY}/LICENSE"' in function
    assert '"${INSTALL_DIRECTORY}/LICENSES"' in function


def test_linux_rollback_removes_incoming_license_material_before_restore():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "replace_failed_application_with_rollback_payload",
    )

    remove_index = function.index("rm -rf")
    restore_license_index = function.index(
        '"${ROLLBACK_APPLICATION_STAGING_ROOT}/LICENSE"'
    )

    removal = function[remove_index:restore_license_index]

    assert '"${INSTALL_DIRECTORY}/LICENSE"' in removal
    assert '"${INSTALL_DIRECTORY}/LICENSES"' in removal


def test_linux_failed_swap_recovery_restores_failed_license_material():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "restore_failed_application_after_swap_failure",
    )

    assert '"${FAILED_APPLICATION_STAGING_DIRECTORY}/LICENSE"' in function
    assert '"${FAILED_APPLICATION_STAGING_DIRECTORY}/LICENSES"' in function

    assert '"${INSTALL_DIRECTORY}/LICENSE"' in function
    assert '"${INSTALL_DIRECTORY}/LICENSES"' in function
