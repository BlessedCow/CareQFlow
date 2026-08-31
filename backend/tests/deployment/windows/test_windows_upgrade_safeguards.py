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
    assert "CareQFlow downgrade refused:" in function
    assert "Compare-CareQueueVersions" in function


def test_windows_upgrade_allows_legacy_install_without_version_metadata():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Assert-CareQueueUpgradeVersion",
    )

    assert "Installed CareQFlow version metadata is unavailable." in function
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

WINDOWS_BACKUP_TASK_INSTALLER = (
    PROJECT_ROOT / "deployment" / "windows" / "install-backup-task.ps1"
)

WINDOWS_BACKUP_TASK_REMOVER = (
    PROJECT_ROOT / "deployment" / "windows" / "remove-backup-task.ps1"
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

    validation_index = content.index("CareQFlow production backend validated.")
    state_index = content.index("Writing CareQFlow installation state...")

    assert validation_index < state_index


def test_windows_existing_environment_migrates_legacy_cors_origin():
    content = _read(WINDOWS_PRODUCTION_INSTALLER)

    migration_block = content.split(
        "$currentCorsOrigins = ConvertTo-Json",
        maxsplit=1,
    )[1].split(
        "$migratedEnvironmentLines +=",
        maxsplit=1,
    )[0]

    assert '["https://carequeue.local"]' in migration_block
    assert (
        '"AUTHSTATUS_CORS_ORIGINS=$currentCorsOrigins"'
        in migration_block
    )


def test_windows_existing_environment_preserves_custom_cors_origin():
    content = _read(WINDOWS_PRODUCTION_INSTALLER)

    migration_block = content.split(
        "$currentCorsOrigins = ConvertTo-Json",
        maxsplit=1,
    )[1].split(
        "$migratedEnvironmentLines +=",
        maxsplit=1,
    )[0]

    legacy_condition_index = migration_block.index(
        '["https://carequeue.local"]'
    )
    replacement_index = migration_block.index(
        '"AUTHSTATUS_CORS_ORIGINS=$currentCorsOrigins"'
    )
    else_index = migration_block.index("else {", replacement_index)
    preserve_index = migration_block.index("$_", else_index)

    assert legacy_condition_index < replacement_index
    assert replacement_index < else_index < preserve_index


def test_windows_upgrade_has_verified_pre_upgrade_backup_helper():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    assert "function New-VerifiedPreUpgradeBackup {" in content

    function = _powershell_function(
        content,
        "New-VerifiedPreUpgradeBackup",
    )

    assert "deployment\\windows\\run-backup.ps1" in function
    assert "Config\\carequeue.env" in function
    assert "*.db.enc" in function
    assert "Verified pre-upgrade backup:" in function


def test_windows_upgrade_backup_requires_new_nonempty_backup():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-VerifiedPreUpgradeBackup",
    )

    assert ".carequeue-pre-upgrade-marker-" in function
    assert "LastWriteTimeUtc" in function
    assert "$newBackups.Count -eq 0" in function
    assert ".Length -le 0" in function


def test_windows_upgrade_backup_failure_states_application_not_replaced():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-VerifiedPreUpgradeBackup",
    )

    assert "The CareQFlow application has not been replaced." in function


def test_windows_upgrade_backup_runs_before_production_installer():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    backup_call_index = content.index(
        "$preUpgradeBackupPath = New-VerifiedPreUpgradeBackup"
    )
    installer_arguments_index = content.index("$installerArguments = @(")

    assert backup_call_index < installer_arguments_index


def test_windows_upgrade_backup_runs_after_logging_is_prepared():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    log_index = content.index("$logPath = Join-Path")
    backup_call_index = content.index(
        "$preUpgradeBackupPath = New-VerifiedPreUpgradeBackup"
    )

    assert log_index < backup_call_index


def test_windows_upgrade_backup_is_upgrade_only():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-VerifiedPreUpgradeBackup",
    )

    assert 'if ($Mode -ne "Upgrade")' in function


def test_windows_upgrade_preserves_previous_application_payload():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-VerifiedPreUpgradeApplicationArchive",
    )

    assert '"backend"' in function
    assert '"frontend"' in function
    assert '"deployment"' in function
    assert '"runtime"' in function
    assert '"vendor"' in function
    assert '"Service"' in function
    assert "Compress-Archive" in function


def test_windows_upgrade_application_archive_requires_valid_version():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-VerifiedPreUpgradeApplicationArchive",
    )

    assert "Test-CareQueueVersion -Version $InstalledVersion" in function
    assert "because its version metadata is invalid:" in function


def test_windows_upgrade_application_archive_is_nonempty_and_hashed():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-VerifiedPreUpgradeApplicationArchive",
    )

    assert "$archiveItem.Length -le 0" in function
    assert "Get-FileHash" in function
    assert "-Algorithm SHA256" in function
    assert "$verificationSha256 -ne $archiveSha256" in function


def test_windows_upgrade_writes_application_checksum_file():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-VerifiedPreUpgradeApplicationArchive",
    )

    assert '$checksumPath = "$archivePath.sha256"' in function
    assert "Set-Content" in function
    assert "$archiveSha256" in function


def test_windows_upgrade_preserves_application_after_database_backup():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    backup_index = content.index("$preUpgradeBackupPath = New-VerifiedPreUpgradeBackup")
    application_index = content.index(
        "New-VerifiedPreUpgradeApplicationArchive",
        backup_index,
    )
    installer_index = content.index("$installerArguments = @(")

    assert backup_index < application_index < installer_index


def test_windows_upgrade_creates_recovery_record():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueUpgradeRecoveryRecord",
    )

    assert "schema_version" in function
    assert "previous_version" in function
    assert "incoming_version" in function
    assert "pre_upgrade_backup" in function
    assert "pre_upgrade_application" in function
    assert "pre_upgrade_application_sha256" in function
    assert "installer_log" in function
    assert "status" in function
    assert '"pending"' in function


def test_windows_upgrade_recovery_record_is_written_atomically():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueUpgradeRecoveryRecord",
    )

    assert '$temporaryRecordPath = "$recordPath.tmp"' in function
    assert "ConvertTo-Json" in function
    assert "Move-Item" in function
    assert "-Destination $recordPath" in function


def test_windows_upgrade_recovery_record_requires_verified_assets():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueUpgradeRecoveryRecord",
    )

    assert "$BackupPath" in function
    assert "$ApplicationArchive" in function
    assert "$ApplicationSha256" in function
    assert "verified pre-upgrade backup is unavailable." in function
    assert "verified pre-upgrade application archive is unavailable." in function


def test_windows_upgrade_recovery_record_created_before_production_installer():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    backup_index = content.index("$preUpgradeBackupPath = New-VerifiedPreUpgradeBackup")
    application_index = content.index(
        "New-VerifiedPreUpgradeApplicationArchive",
        backup_index,
    )
    recovery_index = content.index(
        "$upgradeRecoveryRecord = New-CareQueueUpgradeRecoveryRecord",
        application_index,
    )
    installer_index = content.index("$installerArguments = @(")

    assert backup_index < application_index < recovery_index < installer_index


def test_windows_upgrade_recovery_status_updates_atomically():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Set-CareQueueUpgradeRecoveryStatus",
    )

    assert "ConvertFrom-Json" in function
    assert "$state.status = $Status" in function
    assert '$temporaryRecordPath = "$RecoveryRecord.tmp"' in function
    assert "-Destination $RecoveryRecord" in function


def test_windows_upgrade_tracks_completed_and_failed_recovery_states():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    assert '-Status "completed"' in content
    assert '-Status "failed"' in content


def test_windows_backup_task_installer_uses_careqflow_task_name():
    content = _read(WINDOWS_BACKUP_TASK_INSTALLER)

    assert '[string]$TaskName = "CareQFlow Encrypted Backup"' in content


def test_windows_backup_task_installer_removes_legacy_task():
    content = _read(WINDOWS_BACKUP_TASK_INSTALLER)

    assert '$legacyTaskName = "CareQueue Encrypted Backup"' in content
    assert "Get-ScheduledTask" in content
    assert "-TaskName $legacyTaskName" in content
    assert "Unregister-ScheduledTask" in content
    assert "Removing legacy CareQueue backup task before " in content


def test_windows_backup_task_installer_preserves_custom_task_name():
    content = _read(WINDOWS_BACKUP_TASK_INSTALLER)

    assert "if ($TaskName -ne $legacyTaskName)" in content


def test_windows_backup_task_remover_uses_careqflow_task_name():
    content = _read(WINDOWS_BACKUP_TASK_REMOVER)

    assert '[string]$TaskName = "CareQFlow Encrypted Backup"' in content


def test_windows_backup_task_remover_cleans_up_legacy_task():
    content = _read(WINDOWS_BACKUP_TASK_REMOVER)

    assert '$legacyTaskName = "CareQueue Encrypted Backup"' in content
    assert "$taskNames += $legacyTaskName" in content
    assert "foreach ($candidateTaskName in $taskNames)" in content
    assert "-TaskName $candidateTaskName" in content
    assert "Unregister-ScheduledTask" in content


def test_windows_installer_supports_rollback_mode():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    assert '"Rollback"' in content
    assert "function Get-CareQueueFailedUpgradeRecovery {" in content


def test_windows_rollback_requires_existing_installation():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    assert '"Rollback" {' in content
    assert "there is no " in content
    assert "installation to roll back." in content


def test_windows_rollback_selects_latest_failed_recovery_record():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Get-CareQueueFailedUpgradeRecovery",
    )

    assert '-Filter "upgrade-*.json"' in function
    assert "LastWriteTimeUtc" in function
    assert '[string]$state.status -eq "failed"' in function
    assert "No failed CareQFlow upgrade recovery record was found." in function


def test_windows_rollback_reads_recovery_record_as_json():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Get-CareQueueFailedUpgradeRecovery",
    )

    assert "ConvertFrom-Json" in function
    assert "Invoke-Expression" not in function
    assert "previous_version" in function
    assert "incoming_version" in function
    assert "pre_upgrade_backup" in function


def test_windows_rollback_requires_existing_nonempty_recovery_assets():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Get-CareQueueFailedUpgradeRecovery",
    )

    assert "$backupItem.Length -le 0" in function
    assert "$applicationItem.Length -le 0" in function
    assert "The pre-upgrade rollback backup is empty:" in function
    assert "The pre-upgrade application archive is empty:" in function


def test_windows_rollback_verifies_application_archive_checksum():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Get-CareQueueFailedUpgradeRecovery",
    )

    assert "Get-FileHash" in function
    assert "-Algorithm SHA256" in function
    assert "$calculatedApplicationSha256 -ne $applicationSha256" in function


def test_windows_rollback_application_swap_precedes_database_activation():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_branch = content.split(
        'if ($Mode -eq "Rollback") {',
        maxsplit=1,
    )[
        1
    ].split('if ($Mode -eq "Upgrade") {', maxsplit=1,)[0]

    application_index = rollback_branch.index("Set-CareQueueRollbackApplication")
    staging_index = rollback_branch.index("Invoke-CareQueueRollbackDatabaseStaging")
    activation_index = rollback_branch.index(
        "Invoke-CareQueueRollbackDatabaseActivation"
    )

    assert application_index < staging_index < activation_index
    assert "Pre-upgrade database activated successfully." in rollback_branch
    assert "CareQFlow services started and validated successfully." in rollback_branch


def test_windows_value_returning_helpers_do_not_emit_status_to_pipeline():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    helper_names = (
        "New-VerifiedPreUpgradeBackup",
        "New-VerifiedPreUpgradeApplicationArchive",
        "New-CareQueueUpgradeRecoveryRecord",
    )

    for helper_name in helper_names:
        function = _powershell_function(
            content,
            helper_name,
        )

        assert "Write-Output" not in function


def test_windows_rollback_has_application_staging_helper():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueRollbackApplicationStage",
    )

    assert "Expand-Archive" in function
    assert "$StagingDirectory" in function
    assert "Rollback application payload staged and validated:" in function


def test_windows_rollback_staging_rechecks_archive_checksum():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueRollbackApplicationStage",
    )

    assert "Get-FileHash" in function
    assert "-Algorithm SHA256" in function
    assert "$calculatedSha256 -ne $normalizedExpectedSha256" in function
    assert "Rollback application archive checksum verification failed." in function


def test_windows_rollback_staging_rejects_unsafe_archive_paths():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueRollbackApplicationStage",
    )

    assert "[System.IO.Compression.ZipFile]::OpenRead" in function
    assert "[System.IO.Path]::IsPathRooted" in function
    assert r"'(^|/)\.\.(/|$)'" in function
    assert "unsafe path:" in function


def test_windows_rollback_staging_requires_application_directories():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueRollbackApplicationStage",
    )

    assert '"backend"' in function
    assert '"frontend"' in function
    assert '"deployment"' in function
    assert '"runtime"' in function
    assert '"vendor"' in function
    assert '"Service"' in function
    assert "required directory:" in function


def test_windows_rollback_staging_cleans_partial_extraction_on_failure():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueRollbackApplicationStage",
    )

    assert "catch {" in function
    assert "Remove-Item" in function
    assert "-Recurse" in function
    assert "throw" in function


def test_windows_rollback_stages_application_before_reporting_success():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    staging_index = content.index(
        "New-CareQueueRollbackApplicationStage",
        rollback_index,
    )
    success_index = content.index(
        '"Rollback recovery assets validated successfully."',
        rollback_index,
    )

    assert rollback_index < staging_index < success_index


def test_windows_rollback_has_failed_application_archive_helper():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueFailedApplicationArchive",
    )

    assert "Compress-Archive" in function
    assert "FailedApplications" not in function
    assert "failed-application-" in function
    assert "Get-FileHash" in function
    assert "-Algorithm SHA256" in function


def test_windows_rollback_preserves_partial_failed_application():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueFailedApplicationArchive",
    )

    assert '"backend"' in function
    assert '"frontend"' in function
    assert '"deployment"' in function
    assert '"runtime"' in function
    assert '"vendor"' in function
    assert '"Service"' in function
    assert "existingApplicationPaths" in function
    assert "$existingApplicationPaths.Count -eq 0" in function


def test_windows_rollback_failed_application_archive_is_nonempty():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueFailedApplicationArchive",
    )

    assert "$archiveItem.Length -le 0" in function
    assert "archive is empty:" in function


def test_windows_rollback_failed_application_archive_is_verified():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "New-CareQueueFailedApplicationArchive",
    )

    assert '$checksumPath = "$archivePath.sha256"' in function
    assert "$verificationSha256 -ne $archiveSha256" in function
    assert "checksum " in function
    assert "verification failed." in function


def test_windows_rollback_preserves_failed_application_after_staging():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    staging_index = content.index(
        "New-CareQueueRollbackApplicationStage",
        rollback_index,
    )
    failed_archive_index = content.index(
        "New-CareQueueFailedApplicationArchive",
        rollback_index,
    )
    success_index = content.index(
        '"Rollback recovery assets validated successfully."',
        rollback_index,
    )

    assert rollback_index < staging_index < failed_archive_index < success_index


def test_windows_rollback_logs_failed_application_recovery_assets():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    assert "Failed application archive:" in content
    assert "Failed application SHA256:" in content


def test_windows_upgrade_marks_recovery_failed_before_failure_exit():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    operation_failure_index = content.index('"$Mode operation failed."')

    catch_start = content.rfind(
        "catch {",
        0,
        operation_failure_index,
    )
    catch_end = content.index(
        "\n}",
        operation_failure_index,
    )

    failure_catch = content[catch_start : catch_end + 2]

    status_index = failure_catch.index('-Status "failed"')
    exit_index = failure_catch.index("exit $exitCodeInstallationFailure")

    assert status_index < exit_index


def test_windows_rollback_stops_services_before_application_swap():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Stop-CareQueueServicesForRollback",
    )

    assert '"CareQueueApi"' in function
    assert '"CareQueueCaddy"' in function
    assert "Stop-Service" in function
    assert '"Stopped"' in function


def test_windows_rollback_swap_requires_complete_staged_application():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Set-CareQueueRollbackApplication",
    )

    for directory in (
        "backend",
        "frontend",
        "deployment",
        "runtime",
        "vendor",
        "Service",
    ):
        assert f'"{directory}"' in function

    assert "the staged payload is missing:" in function


def test_windows_rollback_moves_failed_application_before_activation():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Set-CareQueueRollbackApplication",
    )

    failed_move_index = function.index("-Destination $FailedApplicationDirectory")
    staged_move_index = function.index("-Destination $InstallDirectory")

    assert failed_move_index < staged_move_index


def test_windows_rollback_restores_failed_application_on_swap_failure():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Set-CareQueueRollbackApplication",
    )

    assert "Restore-CareQueueFailedApplicationAfterSwapFailure" in function
    assert "$activeApplicationMoved" in function
    assert "throw $swapFailure" in function


def test_windows_rollback_swap_failure_restores_prior_service_state():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Restore-CareQueueFailedApplicationAfterSwapFailure",
    )

    assert "$serviceState.WasRunning" in function
    assert "Start-Service" in function
    assert '"Running"' in function


def test_windows_rollback_application_activation_precedes_success_result():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    activation_index = content.index(
        "Set-CareQueueRollbackApplication",
        rollback_index,
    )
    success_index = content.index(
        '"Previous application payload activated successfully."',
        rollback_index,
    )

    assert rollback_index < activation_index < success_index


def test_windows_rollback_starts_services_after_database_activation():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    activation_index = rollback_branch.index(
        "Invoke-CareQueueRollbackDatabaseActivation"
    )
    service_index = rollback_branch.index("Start-CareQueueServicesAfterRollback")

    assert activation_index < service_index


def test_windows_rollback_service_restart_helper_starts_api_and_caddy():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Start-CareQueueServicesAfterRollback",
    )

    assert '"CareQueueApi"' in function
    assert '"CareQueueCaddy"' in function
    assert "Start-Service" in function
    assert "WaitForStatus" in function
    assert '"Running"' in function


def test_windows_rollback_has_database_staging_helper():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Invoke-CareQueueRollbackDatabaseStaging",
    )

    assert "restore_encrypted_backup.py" in function
    assert "backend\\.venv\\Scripts\\python.exe" in function
    assert "Config\\carequeue.env" in function


def test_windows_rollback_database_staging_requires_backup():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Invoke-CareQueueRollbackDatabaseStaging",
    )

    assert "$BackupPath" in function
    assert "PathType Leaf" in function
    assert "$backupItem.Length -le 0" in function


def test_windows_rollback_database_staging_loads_production_environment():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Invoke-CareQueueRollbackDatabaseStaging",
    )

    assert "Get-Content" in function
    assert "[Environment]::SetEnvironmentVariable" in function
    assert '"Process"' in function


def test_windows_rollback_database_staging_checks_restore_exit_code():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Invoke-CareQueueRollbackDatabaseStaging",
    )

    assert "& $pythonExecutable" in function
    assert "$restoreScript" in function
    assert "$BackupPath" in function
    assert "$LASTEXITCODE -ne 0" in function


def test_windows_rollback_stages_database_after_application_activation():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    application_index = content.index(
        "Set-CareQueueRollbackApplication",
        rollback_index,
    )
    database_index = content.index(
        "Invoke-CareQueueRollbackDatabaseStaging",
        application_index,
    )
    result_index = content.index(
        '"Pre-upgrade database staged successfully."',
        database_index,
    )

    assert rollback_index < application_index < database_index < result_index


def test_windows_rollback_database_staging_does_not_activate_database():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Invoke-CareQueueRollbackDatabaseStaging",
    )

    assert "activate_staged_recovery.py" not in function
    assert "ACTIVATE RECOVERY" not in function


def test_windows_rollback_has_database_activation_helper():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Invoke-CareQueueRollbackDatabaseActivation",
    )

    assert "activate_staged_recovery.py" in function
    assert "backend\\.venv\\Scripts\\python.exe" in function
    assert '"CareQueueApi"' in function
    assert "Data\\auth_tracker.sqlcipher.db" in function
    assert '"Backups"' in function
    assert '"Restores"' in function


def test_windows_rollback_database_activation_checks_exit_code():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Invoke-CareQueueRollbackDatabaseActivation",
    )

    assert "& $pythonExecutable" in function
    assert "$activationScript" in function
    assert "$LASTEXITCODE -ne 0" in function
    assert "CareQFlow services remain stopped." in function


def test_windows_rollback_recovery_status_updates_atomically():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Set-CareQueueRollbackRecoveryStatus",
    )

    assert '"rollback_staged"' in function
    assert '"rollback_activated"' in function
    assert '"rollback_completed"' in function
    assert "ConvertFrom-Json" in function
    assert "$state.status = $Status" in function
    assert '$temporaryRecordPath = "$RecoveryRecord.tmp"' in function
    assert "-Destination $RecoveryRecord" in function


def test_windows_rollback_tracks_staged_then_activated_recovery_states():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    staging_index = rollback_branch.index("Invoke-CareQueueRollbackDatabaseStaging")
    staged_status_index = rollback_branch.index('-Status "rollback_staged"')
    activation_index = rollback_branch.index(
        "Invoke-CareQueueRollbackDatabaseActivation"
    )
    activated_status_index = rollback_branch.index('-Status "rollback_activated"')

    assert (
        staging_index < staged_status_index < activation_index < activated_status_index
    )


def test_windows_rollback_runs_health_validation_after_service_restart():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    service_index = rollback_branch.index("Start-CareQueueServicesAfterRollback")
    health_index = rollback_branch.index("Assert-PostInstallationHealth")

    assert service_index < health_index
    assert "-ApplicationOrigin $ApplicationOrigin" in rollback_branch


def test_windows_rollback_restores_install_state_version_atomically():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Restore-CareQueueRollbackInstallStateVersion",
    )

    assert "Test-CareQueueVersion -Version $PreviousVersion" in function
    assert "ConvertFrom-Json" in function
    assert "$installState.installed_version = $PreviousVersion" in function
    assert '$temporaryInstallStatePath = "$InstallStatePath.tmp"' in function
    assert "-Destination $InstallStatePath" in function


def test_windows_rollback_restores_version_after_health_validation():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    health_index = rollback_branch.index("Assert-PostInstallationHealth")
    state_index = rollback_branch.index("Restore-CareQueueRollbackInstallStateVersion")
    completed_index = rollback_branch.index('-Status "rollback_completed"')

    assert health_index < state_index < completed_index


def test_windows_rollback_cleans_staging_after_completion():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Remove-CareQueueSuccessfulRollbackStaging",
    )

    assert "$rollbackApplicationStagingDirectory" in function
    assert "$failedApplicationStagingDirectory" in function
    assert "Remove-Item" in function
    assert "-Recurse" in function

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    completed_index = rollback_branch.index('-Status "rollback_completed"')
    cleanup_index = rollback_branch.index("Remove-CareQueueSuccessfulRollbackStaging")

    assert completed_index < cleanup_index


def test_windows_rollback_reports_completed_status_after_validation():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    assert "CareQFlow services started and validated successfully." in rollback_branch
    assert "Installed version metadata restored successfully." in rollback_branch
    assert "Upgrade recovery status: rollback_completed" in rollback_branch


def test_windows_rollback_failure_stop_helper_stops_api_and_caddy():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Stop-CareQueueServicesAfterRollbackFailure",
    )

    assert '"CareQueueApi"' in function
    assert '"CareQueueCaddy"' in function
    assert "Stop-Service" in function
    assert "-Force" in function
    assert "WaitForStatus" in function
    assert '"Stopped"' in function


def test_windows_rollback_tracks_database_activation_for_failure_handling():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    initial_index = rollback_branch.index("$rollbackDatabaseActivated = $false")
    activation_index = rollback_branch.index(
        "Invoke-CareQueueRollbackDatabaseActivation"
    )
    activated_index = rollback_branch.index("$rollbackDatabaseActivated = $true")

    assert initial_index < activation_index < activated_index


def test_windows_rollback_failure_does_not_erase_durable_recovery_state():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    failure_message_index = rollback_branch.index(
        "$failureMessage = $_.Exception.Message"
    )
    catch_index = rollback_branch.rfind(
        "catch {",
        0,
        failure_message_index,
    )
    failure_branch = rollback_branch[catch_index:]

    assert "Set-CareQueueRollbackRecoveryStatus" not in failure_branch
    assert "last durable rollback state" in failure_branch


def test_windows_rollback_cleanup_failure_is_nonfatal_after_completion():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    rollback_index = content.index(
        'if ($Mode -eq "Rollback") {',
        content.index("$logPath = Join-Path"),
    )
    upgrade_index = content.index(
        'if ($Mode -eq "Upgrade") {',
        rollback_index,
    )
    rollback_branch = content[rollback_index:upgrade_index]

    completed_index = rollback_branch.index('-Status "rollback_completed"')
    cleanup_index = rollback_branch.index("Remove-CareQueueSuccessfulRollbackStaging")
    cleanup_warning_index = rollback_branch.index(
        "Rollback completed successfully, but temporary "
    )
    success_index = rollback_branch.index(
        '-Status "success"',
        cleanup_warning_index,
    )

    assert completed_index < cleanup_index < cleanup_warning_index < success_index


def test_windows_hostname_registration_removes_legacy_managed_entry():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Set-CareQueueLocalHostname",
    )

    assert "carequeue\\.local" in function
    assert "CareQueue" in function
    assert "$legacyManagedPattern" in function
    assert "Where-Object" in function
    assert "Set-Content" in function


def test_windows_hostname_registration_uses_careqflow_managed_entry():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Set-CareQueueLocalHostname",
    )

    assert "local CareQFlow hostname" in function
    assert "# CareQFlow" in function


def test_windows_hostname_migration_preserves_unmanaged_legacy_mappings():
    content = _read(WINDOWS_INSTALLER_WRAPPER)

    function = _powershell_function(
        content,
        "Set-CareQueueLocalHostname",
    )

    assert "'^\\s*127\\.0\\.0\\.1\\s+carequeue\\.local'" in function
    assert "'\\s+#\\s*CareQueue\\s*$'" in function
