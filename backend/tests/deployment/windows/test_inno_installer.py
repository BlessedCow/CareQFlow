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
        "CareQFlow upgrade." in content
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
        "CareQFlow upgrade." in content
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


def test_inno_installer_network_mode_defaults_to_local_only():
    content = _read_installer()

    assert "function GetInstalledNetworkMode(): String;" in content
    assert "Result := 'LocalOnly';" in content
    assert "CareQueueInstallStatePath" in content


def test_inno_installer_detects_existing_secure_lan_mode():
    content = _read_installer()

    assert '\'"network_mode": "SecureLan"\'' in content
    assert '\'"network_mode":"SecureLan"\'' in content
    assert "Result := 'SecureLan';" in content


def test_inno_installer_offers_explicit_network_mode_choice():
    content = _read_installer()

    assert "NetworkModePage: TInputOptionWizardPage;" in content
    assert "'Choose CareQFlow network access'" in content
    assert "'Local only - use CareQFlow on this computer'" in content
    assert "'Secure LAN - allow devices on the local private network'" in content


def test_inno_installer_requires_secure_lan_confirmation():
    content = _read_installer()

    assert "if SelectedNetworkMode = 'SecureLan' then" in content
    assert "'Enable Secure LAN access?'" in content
    assert "mbConfirmation" in content
    assert "MB_YESNO" in content
    assert "'Do not use router port forwarding to expose '" in content


def test_inno_installer_passes_network_mode_to_install_engine():
    content = _read_installer()

    function_start = content.index("function GetInstallerParameters(): String;")
    function_end = content.index(
        "procedure RunCareQueueInstaller();",
        function_start,
    )
    function = content[function_start:function_end]

    assert "' -NetworkMode '" in function
    assert "QuoteArgument(GetNetworkMode())" in function
    assert "OperationMode <> 'Uninstall'" in function
    assert "OperationMode <> 'Rollback'" in function


def test_inno_installer_does_not_change_network_mode_during_rollback_or_uninstall():
    content = _read_installer()

    assert "PageID = NetworkModePage.ID" in content
    assert "(OperationMode = 'Rollback')" in content
    assert "(OperationMode = 'Uninstall')" in content


def test_inno_installer_preserves_existing_secure_lan_selection():
    content = _read_installer()

    assert "GetInstalledNetworkMode() = 'SecureLan'" in content
    assert "NetworkModePage.Values[1] := True" in content
    assert "NetworkModePage.Values[0] := True" in content


def test_inno_installer_collects_secure_lan_ipv4_address():
    content = _read_installer()

    assert "LanAddressPage: TInputQueryWizardPage;" in content
    assert "'Configure Secure LAN address'" in content
    assert "'Private IPv4 address:'" in content


def test_inno_installer_uses_lan_address_for_secure_lan_origin():
    content = _read_installer()

    assert "function GetApplicationOrigin(): String;" in content
    assert "GetNetworkMode() <> 'SecureLan'" in content
    assert "'https://' +" in content
    assert "LanAddressPage.Values[0]" in content


def test_inno_installer_hides_lan_address_for_local_only():
    content = _read_installer()

    assert "PageID = LanAddressPage.ID" in content
    assert "GetNetworkMode() <> 'SecureLan'" in content


def test_inno_installer_rejects_blank_lan_address():
    content = _read_installer()

    assert "Trim(LanAddressPage.Values[0]) = ''" in content
    assert "'Enter the private IPv4 address assigned to this '" in content
