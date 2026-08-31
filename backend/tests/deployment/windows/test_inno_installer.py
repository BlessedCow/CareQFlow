from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]

WINDOWS_INNO_INSTALLER = (
    PROJECT_ROOT / "deployment" / "windows" / "installer" / "CareQueue.iss"
)


def _read_installer() -> str:
    return WINDOWS_INNO_INSTALLER.read_text(encoding="utf-8")


def test_inno_installer_detects_failed_upgrade_recovery():
    content = _read_installer()

    assert "function CareQueueHasFailedUpgradeRecovery(): Boolean;" in content
    assert "CareQueueUpgradeRecoveryDirectory" in content
    assert "'upgrade-*.json'" in content
    assert '\'"status": "failed"\'' in content
    assert "LoadStringFromFile" in content


def test_inno_installer_only_offers_rollback_when_recovery_exists():
    content = _read_installer()

    assert (
        "RollbackOperationAvailable :=\n"
        "    CareQueueHasFailedUpgradeRecovery();" in content
    )
    assert "if RollbackOperationAvailable then" in content
    assert "'Roll back most recent failed upgrade'" in content


def test_inno_installer_maps_optional_rollback_and_uninstall_rows():
    content = _read_installer()

    assert (
        "else if RollbackOperationAvailable and\n"
        "          OperationModePage.Values[2] then\n"
        "    SelectedOperationMode := 'Rollback'" in content
    )

    assert (
        "else if RollbackOperationAvailable and\n"
        "          OperationModePage.Values[3] then\n"
        "    SelectedOperationMode := 'Uninstall'" in content
    )

    assert (
        "else if (not RollbackOperationAvailable) and\n"
        "          OperationModePage.Values[2] then\n"
        "    SelectedOperationMode := 'Uninstall'" in content
    )


def test_inno_installer_passes_selected_mode_to_powershell():
    content = _read_installer()

    assert "' -Mode '" in content
    assert "OperationMode +" in content
    assert "QuoteArgument(GetInstallerScriptPath())" in content


def test_inno_installer_has_rollback_ready_summary():
    content = _read_installer()

    assert "if OperationMode = 'Rollback' then" in content
    assert (
        "Setup is ready to roll back the most recent failed "
        "CareQueue upgrade." in content
    )
    assert (
        "The verified pre-upgrade application and database recovery "
        "assets will be restored." in content
    )
    assert (
        "Rollback will stop if the required recovery assets "
        "cannot be validated." in content
    )


def test_inno_installer_uses_rollback_ready_button():
    content = _read_installer()

    assert "WizardForm.NextButton.Caption := '&Rollback';" in content
    assert (
        "Click Rollback to recover from the most recent failed "
        "CareQueue upgrade." in content
    )


def test_inno_installer_does_not_offer_admin_setup_after_rollback():
    content = _read_installer()

    function_start = content.index("function ShouldOfferAdminSetup(): Boolean;")
    function_end = content.index(
        "function GetInstallerScriptPath(): String;",
        function_start,
    )
    function = content[function_start:function_end]

    assert "(OperationMode <> 'Uninstall')" in function
    assert "(OperationMode <> 'Rollback')" in function


def test_inno_installer_uses_packaged_license_notice():
    content = _read_installer()

    assert "LicenseFile=..\\..\\..\\build\\windows\\payload\\LICENSE" in content


def test_inno_installer_requires_license_for_install_and_upgrade_only():
    content = _read_installer()

    function_start = content.index("function ShouldSkipPage(PageID: Integer): Boolean;")

    next_function_index = content.find(
        "\nfunction ",
        function_start + 1,
    )

    if next_function_index == -1:
        function = content[function_start:]
    else:
        function = content[function_start:next_function_index]

    assert "PageID = wpLicense" in function
    assert "(OperationMode = 'Repair')" in function
    assert "(OperationMode = 'Rollback')" in function
    assert "(OperationMode = 'Uninstall')" in function

    assert "(OperationMode = 'Install')" not in function
    assert "(OperationMode = 'Upgrade')" not in function
