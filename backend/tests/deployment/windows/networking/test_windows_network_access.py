from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]

WINDOWS_NETWORK_ACCESS = (
    PROJECT_ROOT
    / "deployment"
    / "windows"
    / "networking"
    / "Set-CareQFlowNetworkAccess.ps1"
)

WINDOWS_PRODUCTION_INSTALLER = (
    PROJECT_ROOT / "deployment" / "windows" / "install-production.ps1"
)

WINDOWS_INSTALLER_WRAPPER = (
    PROJECT_ROOT / "deployment" / "windows" / "installer" / "invoke-install.ps1"
)


def _read() -> str:
    return WINDOWS_NETWORK_ACCESS.read_text(encoding="utf-8")


def test_windows_network_access_defaults_to_local_only():
    content = _read()

    assert '"LocalOnly"' in content
    assert '"SecureLan"' in content
    assert '[string]$NetworkMode = "LocalOnly"' in content


def test_windows_secure_lan_exposes_only_https():
    content = _read()

    assert "-Direction Inbound" in content
    assert "-Action Allow" in content
    assert "-Protocol TCP" in content
    assert "-LocalPort 443" in content

    assert "8000" not in content


def test_windows_secure_lan_is_private_network_only():
    content = _read()

    assert "-Profile Private" in content
    assert "-RemoteAddress LocalSubnet" in content
    assert "-EdgeTraversalPolicy Block" in content


def test_windows_secure_lan_rule_is_scoped_to_caddy():
    content = _read()

    assert "-Program $resolvedCaddyExecutable" in content
    assert "Resolve-Path" in content
    assert "$CaddyExecutable" in content


def test_windows_local_only_removes_secure_lan_rule():
    content = _read()

    local_only_branch = content.split(
        '"LocalOnly" {',
        maxsplit=1,
    )[1].split(
        '"SecureLan" {',
        maxsplit=1,
    )[0]

    assert "Remove-CareQFlowSecureLanFirewallRule" in local_only_branch
    assert "Enable-CareQFlowSecureLanFirewallRule" not in local_only_branch


def test_windows_secure_lan_replaces_existing_rule():
    content = _read()

    function = content.split(
        "function Enable-CareQFlowSecureLanFirewallRule {",
        maxsplit=1,
    )[1].split("if (-not (Test-Administrator))", maxsplit=1,)[0]

    assert "Remove-CareQFlowSecureLanFirewallRule" in function
    assert "New-NetFirewallRule" in function


def test_windows_network_access_requires_administrator():
    content = _read()

    assert "Test-Administrator" in content
    assert "CareQFlow network access configuration requires " in content


def test_windows_production_installer_defaults_to_local_only():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert '[string]$NetworkMode = "LocalOnly"' in content
    assert '"LocalOnly"' in content
    assert '"SecureLan"' in content


def test_windows_production_installer_requires_network_access_script():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert (
        '"deployment\\windows\\networking\\' 'Set-CareQFlowNetworkAccess.ps1"'
    ) in content


def test_windows_production_installer_applies_selected_network_mode():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert '"windows\\networking\\Set-CareQFlowNetworkAccess.ps1"' in content
    assert "-NetworkMode $NetworkMode" in content
    assert "-CaddyExecutable $installedCaddyExecutable" in content


def test_windows_install_state_records_network_mode():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "network_mode       = $NetworkMode" in content


def test_windows_installer_wrapper_preserves_existing_network_mode():
    content = WINDOWS_INSTALLER_WRAPPER.read_text(encoding="utf-8")

    assert "function Get-CareQueueInstalledNetworkMode {" in content
    assert "$installedNetworkMode -notin @(" in content
    assert 'return "LocalOnly"' in content

    assert ("$resolvedNetworkMode = " "Get-CareQueueInstalledNetworkMode") in content


def test_windows_installer_wrapper_defaults_legacy_install_to_local_only():
    content = WINDOWS_INSTALLER_WRAPPER.read_text(encoding="utf-8")

    function = content.split(
        "function Get-CareQueueInstalledNetworkMode {",
        maxsplit=1,
    )[1].split("function ", maxsplit=1,)[0]

    assert "$null -eq $installState.network_mode" in function
    assert 'return "LocalOnly"' in function


def test_windows_installer_passes_resolved_network_mode_to_production_install():
    content = WINDOWS_INSTALLER_WRAPPER.read_text(encoding="utf-8")

    installer_arguments = content.split(
        "$installerArguments = @(",
        maxsplit=1,
    )[1]

    assert '"-NetworkMode",' in installer_arguments
    assert "$resolvedNetworkMode," in installer_arguments


def test_windows_installer_logs_resolved_network_mode():
    content = WINDOWS_INSTALLER_WRAPPER.read_text(encoding="utf-8")

    assert '"Network mode: $resolvedNetworkMode"' in content


def test_secure_lan_accepts_only_private_ipv4_origins():
    content = WINDOWS_INSTALLER_WRAPPER.read_text(encoding="utf-8")

    assert "function Test-CareQFlowPrivateLanIPv4Address {" in content
    assert "$bytes[0] -eq 10" in content
    assert "$bytes[0] -eq 172" in content
    assert "$bytes[0] -eq 192" in content
    assert "$bytes[1] -eq 168" in content


def test_secure_lan_requires_https_port_443():
    content = WINDOWS_INSTALLER_WRAPPER.read_text(encoding="utf-8")

    assert "function Assert-CareQFlowNetworkOrigin {" in content
    assert '$applicationUri.Scheme -ne "https"' in content
    assert "$applicationUri.Port -ne 443" in content


def test_secure_lan_origin_validation_uses_resolved_network_mode():
    content = WINDOWS_INSTALLER_WRAPPER.read_text(encoding="utf-8")

    assert "Assert-CareQFlowNetworkOrigin" in content
    assert "-NetworkMode $resolvedNetworkMode" in content
    assert "-ApplicationOrigin $ApplicationOrigin" in content
