from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

LINUX_INSTALLER_WRAPPER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "invoke-install.sh"
)

LINUX_PACKAGE_BUILDER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "build-payload.ps1"
)

LINUX_PRODUCTION_INSTALLER = (
    PROJECT_ROOT / "deployment" / "linux" / "install-production.sh"
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


def test_linux_package_contains_versioned_release_metadata():
    content = _read(LINUX_PACKAGE_BUILDER)

    assert '"carequeue-release.env"' in content
    assert '"CAREQUEUE_RELEASE_METADATA_SCHEMA=1"' in content
    assert '"CAREQUEUE_APP_VERSION=$Version"' in content
    assert '"CAREQUEUE_PACKAGE_PLATFORM=linux"' in content


def test_linux_installer_requires_release_metadata():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    assert (
        'RELEASE_METADATA_FILE="${SOURCE_DIRECTORY}/carequeue-release.env"' in content
    )

    validate_source = _shell_function(
        content,
        "validate_source",
    )

    assert '"carequeue-release.env"' in validate_source


def test_linux_installer_validates_release_metadata_before_installation():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    assert "validate_release_metadata()" in content

    main_function = _shell_function(
        content,
        "main",
    )

    metadata_index = main_function.index(
        "validate_release_metadata",
    )
    dependency_index = main_function.index(
        "install_system_dependencies",
    )
    copy_index = main_function.index(
        "copy_application_files",
    )

    assert metadata_index < dependency_index
    assert metadata_index < copy_index


def test_linux_release_metadata_is_parsed_as_data():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_release_metadata",
    )

    assert "while IFS='=' read -r key value" in function
    assert 'done < "${RELEASE_METADATA_FILE}"' in function

    assert 'source "${RELEASE_METADATA_FILE}"' not in function
    assert '. "${RELEASE_METADATA_FILE}"' not in function


def test_linux_installer_persists_installed_release_version():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "write_installation_state",
    )

    assert "CAREQUEUE_INSTALL_STATE_SCHEMA=1" in function
    assert "CAREQUEUE_INSTALLED_VERSION=${RELEASE_APP_VERSION}" in function
    assert "CAREQUEUE_PACKAGE_PLATFORM=${RELEASE_PACKAGE_PLATFORM}" in function


def test_linux_upgrade_requires_valid_incoming_version():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "validate_upgrade_version",
    )

    assert 'if [[ "${MODE}" != "upgrade" ]]' in function
    assert 'if [[ ! -f "${RELEASE_METADATA_FILE}" ]]' in function
    assert '"CAREQUEUE_APP_VERSION"' in function
    assert 'validate_version_string "${INCOMING_VERSION}"' in function


def test_linux_upgrade_rejects_same_version_and_downgrade():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "validate_upgrade_version",
    )

    assert "Use repair instead of upgrade." in function
    assert "CareQueue downgrade refused:" in function
    assert "compare_versions" in function


def test_linux_upgrade_allows_legacy_install_without_version_metadata():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "validate_upgrade_version",
    )

    assert "Installed CareQueue version metadata is unavailable." in function
    assert "Continuing legacy upgrade validation." in function


def test_linux_upgrade_requires_backup_service_and_script():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "create_verified_pre_upgrade_backup",
    )

    assert "/etc/systemd/system/carequeue-backup.service" in function
    assert "backend/scripts/create_encrypted_backup.py" in function
    assert 'if [[ ! -f "${backup_service}" ]]' in function
    assert 'if [[ ! -f "${backup_script}" ]]' in function


def test_linux_upgrade_requires_production_configuration_before_backup():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "create_verified_pre_upgrade_backup",
    )

    assert 'if [[ ! -f "${CONFIG_DIRECTORY}/carequeue.env" ]]' in function


def test_linux_upgrade_backup_failure_aborts_before_installation():
    content = _read(LINUX_INSTALLER_WRAPPER)

    backup_function = _shell_function(
        content,
        "create_verified_pre_upgrade_backup",
    )

    assert "systemctl start carequeue-backup.service" in backup_function
    assert "Pre-upgrade backup creation or verification failed." in backup_function
    assert "The CareQueue application has not been replaced." in backup_function

    main_function = _shell_function(
        content,
        "main",
    )

    backup_index = main_function.index(
        "create_verified_pre_upgrade_backup",
    )
    case_index = main_function.index(
        'case "${MODE}" in',
    )

    assert backup_index < case_index


def test_linux_upgrade_requires_new_nonempty_backup():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "create_verified_pre_upgrade_backup",
    )

    assert "mktemp" in function
    assert "-newer" in function
    assert "-name '*.db.enc'" in function
    assert 'if [[ -z "${backup_path}" ]]' in function
    assert 'if [[ ! -s "${backup_path}" ]]' in function
    assert "Verified pre-upgrade backup:" in function


def test_linux_upgrade_validation_runs_before_logging_and_backup():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    version_index = main_function.index(
        "validate_upgrade_version",
    )
    logging_index = main_function.index(
        "prepare_logging",
    )
    backup_index = main_function.index(
        "create_verified_pre_upgrade_backup",
    )

    assert version_index < logging_index
    assert logging_index < backup_index


def test_linux_upgrade_does_not_replace_application_before_verified_backup():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    backup_index = main_function.index(
        "create_verified_pre_upgrade_backup",
    )

    upgrade_case = main_function.split(
        "upgrade)",
        maxsplit=1,
    )[1].split(
        ";;",
        maxsplit=1,
    )[0]

    assert "run_install_operation" in upgrade_case
    assert backup_index < main_function.index(
        'case "${MODE}" in',
    )
