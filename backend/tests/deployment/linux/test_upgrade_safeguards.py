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


def test_linux_upgrade_tracks_verified_backup_for_recovery():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "create_verified_pre_upgrade_backup",
    )

    assert 'PRE_UPGRADE_BACKUP_PATH="${backup_path}"' in function
    assert "Verified pre-upgrade backup: %s" in function


def test_linux_upgrade_creates_recovery_record_before_installation():
    content = _read(LINUX_INSTALLER_WRAPPER)

    assert "write_upgrade_recovery_record()" in content

    function = _shell_function(
        content,
        "write_upgrade_recovery_record",
    )

    assert "CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1" in function
    assert "CAREQUEUE_PREVIOUS_VERSION=${INSTALLED_VERSION:-unknown}" in function
    assert "CAREQUEUE_INCOMING_VERSION=${INCOMING_VERSION}" in function
    assert "CAREQUEUE_PRE_UPGRADE_BACKUP=${PRE_UPGRADE_BACKUP_PATH}" in function
    assert "CAREQUEUE_INSTALLER_LOG=${LOG_PATH}" in function
    assert "CAREQUEUE_UPGRADE_STATUS=pending" in function

    main_function = _shell_function(
        content,
        "main",
    )

    recovery_index = main_function.index(
        "write_upgrade_recovery_record",
    )
    case_index = main_function.index(
        'case "${MODE}" in',
    )

    assert recovery_index < case_index


def test_linux_upgrade_recovery_record_requires_verified_backup():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "write_upgrade_recovery_record",
    )

    assert 'if [[ -z "${PRE_UPGRADE_BACKUP_PATH}" ]]' in function
    assert "Cannot create upgrade recovery state because the " in function


def test_linux_upgrade_recovery_status_updates_atomically():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "update_upgrade_recovery_status",
    )

    assert 'temporary_record="${UPGRADE_RECOVERY_RECORD}.tmp"' in function
    assert "replacement_status" in function
    assert 'mv -f "${temporary_record}" "${UPGRADE_RECOVERY_RECORD}"' in function


def test_linux_upgrade_marks_recovery_record_completed_or_failed():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    upgrade_case = main_function.split(
        "upgrade)",
        maxsplit=1,
    )[1].split(
        ";;",
        maxsplit=1,
    )[0]

    assert 'update_upgrade_recovery_status "completed"' in upgrade_case
    assert 'update_upgrade_recovery_status "failed"' in upgrade_case
    assert "Recovery information was preserved at:" in upgrade_case


def test_linux_installer_supports_rollback_mode():
    content = _read(LINUX_INSTALLER_WRAPPER)

    assert "install|upgrade|repair|rollback|uninstall" in content
    assert "upgrade|repair|rollback)" in content


def test_linux_rollback_resolves_latest_failed_upgrade_record():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_failed_upgrade_recovery_record",
    )

    assert "-name 'upgrade-*.env'" in function
    assert '"CAREQUEUE_UPGRADE_STATUS"' in function
    assert 'if [[ "${record_status}" == "failed" ]]' in function
    assert "No failed CareQueue upgrade recovery record was found." in function


def test_linux_rollback_loads_recovery_metadata_as_data():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_failed_upgrade_recovery_record",
    )

    assert '"CAREQUEUE_PREVIOUS_VERSION"' in function
    assert '"CAREQUEUE_INCOMING_VERSION"' in function
    assert '"CAREQUEUE_PRE_UPGRADE_BACKUP"' in function

    assert 'source "${ROLLBACK_RECOVERY_RECORD}"' not in function
    assert '. "${ROLLBACK_RECOVERY_RECORD}"' not in function


def test_linux_rollback_requires_existing_nonempty_backup():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_failed_upgrade_recovery_record",
    )

    assert 'if [[ -z "${ROLLBACK_BACKUP_PATH}" ]]' in function
    assert 'if [[ ! -f "${ROLLBACK_BACKUP_PATH}" ]]' in function
    assert 'if [[ ! -s "${ROLLBACK_BACKUP_PATH}" ]]' in function


def test_linux_rollback_uses_existing_restore_tooling():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "prepare_failed_upgrade_rollback",
    )

    assert "backend/scripts/restore_encrypted_backup.py" in function
    assert '"${ROLLBACK_BACKUP_PATH}"' in function
    assert "rollback preparation failed" in function


def test_linux_rollback_does_not_claim_database_activation():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "prepare_failed_upgrade_rollback",
    )

    assert "The active database has not been replaced." in function
    assert (
        "Complete recovery activation using the staged CareQueue recovery workflow."
        in function
    )


def test_linux_rollback_resolves_recovery_state_before_operation():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    resolve_index = main_function.index(
        "resolve_failed_upgrade_recovery_record",
    )
    case_index = main_function.index(
        'case "${MODE}" in',
    )

    assert resolve_index < case_index

    rollback_case = main_function.split(
        "rollback)",
        maxsplit=1,
    )[1].split(
        ";;",
        maxsplit=1,
    )[0]

    assert "prepare_failed_upgrade_rollback" in rollback_case


def test_linux_rollback_status_updates_atomically():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "update_rollback_recovery_status",
    )

    assert 'temporary_record="${ROLLBACK_RECOVERY_RECORD}.tmp"' in function
    assert "replacement_status" in function
    assert 'mv -f "${temporary_record}" "${ROLLBACK_RECOVERY_RECORD}"' in function


def test_linux_rollback_marks_record_staged_only_after_restore():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "prepare_failed_upgrade_rollback",
    )

    restore_index = function.index(
        '"${restore_script}"',
    )
    staged_index = function.index(
        'update_rollback_recovery_status "rollback_staged"',
    )

    assert restore_index < staged_index
    assert "Upgrade recovery status: rollback_staged" in function


def test_linux_rollback_activation_uses_existing_recovery_tooling():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    assert "backend/scripts/activate_staged_recovery.py" in function
    assert "--service-name carequeue-api.service" in function
    assert "--backup-directory" in function
    assert "--restore-directory" in function


def test_linux_rollback_stops_api_before_database_activation():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    stop_index = function.index(
        "systemctl stop carequeue-api.service",
    )
    activation_index = function.index(
        "systemd-run",
    )

    assert stop_index < activation_index


def test_linux_rollback_keeps_api_stopped_when_activation_fails():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    assert "CareQueue API remains stopped for safety." in function
    assert (
        "Review the recovery output before attempting another recovery operation."
        in function
    )


def test_linux_rollback_marks_activation_before_restarting_api():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    status_index = function.index(
        'update_rollback_recovery_status "rollback_activated"',
    )
    start_index = function.index(
        "systemctl start carequeue-api.service",
    )

    assert status_index < start_index


def test_linux_rollback_case_stages_before_activation():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    rollback_case = main_function.split(
        "rollback)",
        maxsplit=1,
    )[1].split(
        ";;",
        maxsplit=1,
    )[0]

    staging_index = rollback_case.index(
        "prepare_failed_upgrade_rollback",
    )
    activation_index = rollback_case.index(
        "activate_failed_upgrade_rollback",
    )

    assert staging_index < activation_index


def test_linux_rollback_marks_completed_only_after_api_restart():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    start_index = function.index(
        "systemctl start carequeue-api.service",
    )
    completed_index = function.index(
        'update_rollback_recovery_status "rollback_completed"',
    )

    assert start_index < completed_index


def test_linux_rollback_reports_completed_status():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    assert "Upgrade recovery status: rollback_completed" in function


def test_linux_rollback_restores_previous_installed_version_atomically():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "restore_previous_install_state_version",
    )

    assert 'validate_version_string "${ROLLBACK_PREVIOUS_VERSION}"' in function
    assert 'temporary_state="${INSTALL_STATE_FILE}.tmp"' in function
    assert "CAREQUEUE_INSTALLED_VERSION=" in function
    assert 'mv -f "${temporary_state}" "${INSTALL_STATE_FILE}"' in function


def test_linux_rollback_does_not_source_installation_state():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "restore_previous_install_state_version",
    )

    assert 'source "${INSTALL_STATE_FILE}"' not in function
    assert '. "${INSTALL_STATE_FILE}"' not in function


def test_linux_rollback_restores_version_before_marking_completed():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    restore_index = function.index(
        "restore_previous_install_state_version",
    )
    completed_index = function.index(
        'update_rollback_recovery_status "rollback_completed"',
    )

    assert restore_index < completed_index


def test_linux_upgrade_preserves_previous_application_payload():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "create_verified_pre_upgrade_application_archive",
    )

    assert '"${INSTALL_DIRECTORY}/backend"' in function
    assert '"${INSTALL_DIRECTORY}/frontend"' in function
    assert '"${INSTALL_DIRECTORY}/deployment"' in function
    assert "--exclude='backend/.venv'" in function
    assert "sha256sum" in function


def test_linux_upgrade_application_payload_requires_valid_installed_version():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "create_verified_pre_upgrade_application_archive",
    )

    assert 'validate_version_string "${INSTALLED_VERSION}"' in function
    assert (
        "application rollback payload will not be created for this legacy upgrade"
        in function
    )


def test_linux_upgrade_records_previous_application_payload():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "write_upgrade_recovery_record",
    )

    assert (
        "CAREQUEUE_PRE_UPGRADE_APPLICATION=${PRE_UPGRADE_APPLICATION_ARCHIVE}"
        in function
    )
    assert (
        "CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256="
        "${PRE_UPGRADE_APPLICATION_SHA256}" in function
    )


def test_linux_upgrade_preserves_application_before_replacement():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    backup_index = main_function.index(
        "create_verified_pre_upgrade_backup",
    )
    application_index = main_function.index(
        "create_verified_pre_upgrade_application_archive",
    )
    recovery_index = main_function.index(
        "write_upgrade_recovery_record",
    )
    case_index = main_function.index(
        'case "${MODE}" in',
    )

    assert backup_index < application_index
    assert application_index < recovery_index
    assert recovery_index < case_index


def test_linux_upgrade_application_archive_is_verified_before_use():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "create_verified_pre_upgrade_application_archive",
    )

    archive_index = function.index(
        "tar \\",
    )
    checksum_index = function.index(
        'PRE_UPGRADE_APPLICATION_SHA256="$(',
    )
    verification_index = function.index(
        'if [[ "${calculated_checksum}" != "${PRE_UPGRADE_APPLICATION_SHA256}" ]]',
    )

    assert archive_index < checksum_index < verification_index


def test_linux_rollback_loads_previous_application_metadata():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_failed_upgrade_recovery_record",
    )

    assert '"CAREQUEUE_PRE_UPGRADE_APPLICATION"' in function
    assert '"CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256"' in function


def test_linux_rollback_requires_existing_application_archive():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_failed_upgrade_recovery_record",
    )

    assert 'if [[ -z "${ROLLBACK_APPLICATION_ARCHIVE}" ]]' in function
    assert 'if [[ ! -f "${ROLLBACK_APPLICATION_ARCHIVE}" ]]' in function
    assert 'if [[ ! -s "${ROLLBACK_APPLICATION_ARCHIVE}" ]]' in function


def test_linux_rollback_requires_valid_application_checksum():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_failed_upgrade_recovery_record",
    )

    assert '[[ ! "${ROLLBACK_APPLICATION_SHA256}" =~ ^[0-9a-f]{64}$ ]]' in function
    assert "sha256sum" in function
    assert (
        'if [[ "${calculated_application_sha256}" != '
        '"${ROLLBACK_APPLICATION_SHA256}" ]]' in function
    )
    assert "Pre-upgrade application archive checksum verification failed." in function


def test_linux_rollback_reports_verified_application_payload():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_failed_upgrade_recovery_record",
    )

    assert "Pre-upgrade application: %s" in function
    assert "Verified application SHA256: %s" in function


def test_linux_rollback_stages_application_in_isolated_directory():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "stage_verified_rollback_application",
    )

    assert "mktemp" in function
    assert "--directory" in function
    assert '"${ROLLBACK_APPLICATION_ARCHIVE}"' in function


def test_linux_rollback_validates_staged_application_structure():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "stage_verified_rollback_application",
    )

    assert '"${ROLLBACK_APPLICATION_STAGING_ROOT}/backend"' in function
    assert '"${ROLLBACK_APPLICATION_STAGING_ROOT}/frontend"' in function
    assert '"${ROLLBACK_APPLICATION_STAGING_ROOT}/deployment"' in function
    assert (
        "The staged rollback application payload is missing required "
        "application directories." in function
    )


def test_linux_rollback_rejects_archived_virtual_environment():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "stage_verified_rollback_application",
    )

    assert '"${ROLLBACK_APPLICATION_STAGING_ROOT}/backend/.venv"' in function
    assert (
        "The rollback application payload unexpectedly contains a "
        "Python virtual environment." in function
    )


def test_linux_rollback_stages_application_before_database_recovery():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    rollback_case = main_function.split(
        "rollback)",
        maxsplit=1,
    )[1].split(
        ";;",
        maxsplit=1,
    )[0]

    application_index = rollback_case.index(
        "stage_verified_rollback_application",
    )
    database_index = rollback_case.index(
        "prepare_failed_upgrade_rollback",
    )

    assert application_index < database_index


def test_linux_rollback_preserves_failed_application_before_replacement():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "preserve_failed_application_before_rollback",
    )

    assert '"${INSTALL_DIRECTORY}/backend"' in function
    assert '"${INSTALL_DIRECTORY}/frontend"' in function
    assert '"${INSTALL_DIRECTORY}/deployment"' in function
    assert "--exclude='backend/.venv'" in function
    assert "sha256sum" in function


def test_linux_rollback_verifies_failed_application_archive():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "preserve_failed_application_before_rollback",
    )

    assert 'if [[ ! -s "${FAILED_APPLICATION_ARCHIVE}" ]]' in function
    assert (
        'if [[ "${calculated_checksum}" != "${FAILED_APPLICATION_SHA256}" ]]'
        in function
    )
    assert "Failed application archive checksum verification failed." in function


def test_linux_rollback_records_failed_application_atomically():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "record_failed_application_for_rollback",
    )

    assert "CAREQUEUE_FAILED_APPLICATION=" in function
    assert "CAREQUEUE_FAILED_APPLICATION_SHA256=" in function
    assert 'temporary_record="${ROLLBACK_RECOVERY_RECORD}.tmp"' in function
    assert 'mv -f "${temporary_record}" "${ROLLBACK_RECOVERY_RECORD}"' in function


def test_linux_rollback_preserves_failed_application_before_database_recovery():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    rollback_case = main_function.split(
        "rollback)",
        maxsplit=1,
    )[1].split(
        ";;",
        maxsplit=1,
    )[0]

    stage_index = rollback_case.index(
        "stage_verified_rollback_application",
    )
    preserve_index = rollback_case.index(
        "preserve_failed_application_before_rollback",
    )
    record_index = rollback_case.index(
        "record_failed_application_for_rollback",
    )
    database_index = rollback_case.index(
        "prepare_failed_upgrade_rollback",
    )

    assert stage_index < preserve_index
    assert preserve_index < record_index
    assert record_index < database_index


def test_linux_rollback_moves_failed_application_before_restoring_previous():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "replace_failed_application_with_rollback_payload",
    )

    move_index = function.index(
        'mv \\\n        "${INSTALL_DIRECTORY}/backend"',
    )
    restore_index = function.index(
        "cp -a --no-preserve=context \\\n        "
        '"${ROLLBACK_APPLICATION_STAGING_ROOT}/backend"',
    )

    assert move_index < restore_index
    assert "FAILED_APPLICATION_STAGING_DIRECTORY" in function


def test_linux_rollback_rebuilds_previous_python_environment():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "replace_failed_application_with_rollback_payload",
    )

    assert "python3 -m venv" in function
    assert 'requirements.txt"' in function
    assert "-c 'import authstatus_api.main'" in function


def test_linux_rollback_restores_application_before_database_recovery():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    rollback_case = main_function.split(
        "rollback)",
        maxsplit=1,
    )[1].split(
        ";;",
        maxsplit=1,
    )[0]

    application_index = rollback_case.index(
        "replace_failed_application_with_rollback_payload",
    )
    service_index = rollback_case.index(
        "restore_rollback_service_definitions",
    )
    database_index = rollback_case.index(
        "prepare_failed_upgrade_rollback",
    )

    assert application_index < service_index < database_index


def test_linux_rollback_restores_previous_systemd_units():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "restore_rollback_service_definitions",
    )

    assert "carequeue-api.service" in function
    assert "carequeue-backup.service" in function
    assert "carequeue-backup.timer" in function
    assert "carequeue-caddy.service" in function
    assert "systemctl daemon-reload" in function


def test_linux_rollback_can_restore_failed_application_after_swap_failure():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "restore_failed_application_after_swap_failure",
    )

    assert "rm -rf \\" in function
    assert '"${FAILED_APPLICATION_STAGING_DIRECTORY}/backend"' in function
    assert '"${FAILED_APPLICATION_STAGING_DIRECTORY}/frontend"' in function
    assert '"${FAILED_APPLICATION_STAGING_DIRECTORY}/deployment"' in function
    assert "Failed application restored after rollback replacement failure." in function


def test_linux_rollback_copy_failures_restore_failed_application():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "replace_failed_application_with_rollback_payload",
    )

    assert function.count("restore_failed_application_after_swap_failure") >= 3

    assert (
        "The failed application was restored and CareQueue services remain stopped."
        in function
    )


def test_linux_rollback_environment_failures_restore_failed_application():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "replace_failed_application_with_rollback_payload",
    )

    venv_index = function.index(
        'python3 -m venv "${virtual_environment}"',
    )
    dependency_index = function.index(
        '--requirement "${backend_directory}/requirements.txt"',
    )
    validation_index = function.index(
        "-c 'import authstatus_api.main'",
    )

    assert "restore_failed_application_after_swap_failure" in function
    assert venv_index < dependency_index < validation_index


def test_linux_rollback_does_not_continue_after_application_swap_failure():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "replace_failed_application_with_rollback_payload",
    )

    assert "CareQueue services remain stopped." in function
    assert "fail \\" in function


def test_linux_failed_application_restore_records_recovery_state():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "restore_failed_application_after_swap_failure",
    )

    assert 'update_rollback_recovery_status "rollback_application_restored"' in function
    assert "Upgrade recovery status: rollback_application_restored" in function


def test_linux_failed_application_restore_keeps_services_stopped():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "restore_failed_application_after_swap_failure",
    )

    assert "CareQueue services remain stopped pending administrator review." in function
    assert "systemctl start carequeue-api.service" not in function
    assert "systemctl start carequeue-caddy.service" not in function


def test_linux_successful_rollback_cleans_temporary_application_staging():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "cleanup_successful_rollback_staging",
    )

    assert '"${ROLLBACK_APPLICATION_STAGING_DIRECTORY}"' in function
    assert '"${FAILED_APPLICATION_STAGING_DIRECTORY}"' in function
    assert 'rm -rf "${ROLLBACK_APPLICATION_STAGING_DIRECTORY}"' in function
    assert 'rm -rf "${FAILED_APPLICATION_STAGING_DIRECTORY}"' in function


def test_linux_rollback_cleans_staging_only_after_completion_state():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    completed_index = function.index(
        'update_rollback_recovery_status "rollback_completed"',
    )
    cleanup_index = function.index(
        "cleanup_successful_rollback_staging",
    )

    assert completed_index < cleanup_index


def test_linux_rollback_cleanup_does_not_delete_durable_recovery_assets():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "cleanup_successful_rollback_staging",
    )

    assert "ROLLBACK_BACKUP_PATH" not in function
    assert "ROLLBACK_APPLICATION_ARCHIVE" not in function
    assert "FAILED_APPLICATION_ARCHIVE" not in function
    assert "ROLLBACK_RECOVERY_RECORD" not in function


def test_linux_rollback_restarts_api_and_caddy_before_completion():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    api_index = function.index(
        "systemctl start carequeue-api.service",
    )
    caddy_index = function.index(
        "systemctl start carequeue-caddy.service",
    )
    completed_index = function.index(
        'update_rollback_recovery_status "rollback_completed"',
    )

    assert api_index < caddy_index < completed_index


def test_linux_rollback_validates_health_and_readiness():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "validate_post_rollback_health",
    )

    assert "/api/health" in function
    assert "/api/health/ready" in function
    assert "--fail" in function
    assert "--insecure" in function
    assert "seq 1 30" in function


def test_linux_rollback_health_uses_recorded_application_origin():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "validate_post_rollback_health",
    )

    assert '"CAREQUEUE_APPLICATION_ORIGIN"' in function
    assert 'application_origin="https://carequeue.local"' in function


def test_linux_rollback_health_validation_precedes_completion():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    health_index = function.index(
        "validate_post_rollback_health",
    )
    version_index = function.index(
        "restore_previous_install_state_version",
    )
    completed_index = function.index(
        'update_rollback_recovery_status "rollback_completed"',
    )

    assert health_index < version_index < completed_index


def test_linux_rollback_health_failure_does_not_claim_completion():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "validate_post_rollback_health",
    )

    assert (
        "Recovery remains activated, but rollback was not marked complete." in function
    )


def test_linux_rollback_restores_backup_timer():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    assert "systemctl enable --now carequeue-backup.timer" in function


def test_linux_rollback_validates_required_services():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "validate_post_rollback_services",
    )

    assert "carequeue-api.service" in function
    assert "carequeue-caddy.service" in function
    assert "carequeue-backup.timer" in function
    assert "systemctl is-active --quiet" in function


def test_linux_rollback_service_validation_precedes_health_check():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "activate_failed_upgrade_rollback",
    )

    service_index = function.index(
        "validate_post_rollback_services",
    )
    health_index = function.index(
        "validate_post_rollback_health",
    )
    completed_index = function.index(
        'update_rollback_recovery_status "rollback_completed"',
    )

    assert service_index < health_index < completed_index
