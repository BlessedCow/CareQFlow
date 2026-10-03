from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]

CLIENT_TRUST_EXPORT = (
    PROJECT_ROOT
    / "deployment"
    / "windows"
    / "networking"
    / "Export-CareQFlowClientTrust.ps1"
)

PRODUCTION_INSTALLER = (
    PROJECT_ROOT / "deployment" / "windows" / "install-production.ps1"
)

INSTALLER_WRAPPER = (
    PROJECT_ROOT / "deployment" / "windows" / "installer" / "invoke-install.ps1"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_client_trust_export_uses_caddy_public_root_certificate():
    content = _read(CLIENT_TRUST_EXPORT)

    assert '"Caddy\\Data\\caddy\\pki\\authorities\\local\\root.crt"' in content
    assert '"CareQFlow-Root-CA.crt"' in content


def test_client_trust_export_rejects_private_key_material():
    content = _read(CLIENT_TRUST_EXPORT)

    assert "$rootCertificate.HasPrivateKey" in content
    assert "$exportedCertificate.HasPrivateKey" in content

    assert '".key"' in content
    assert '".pfx"' in content
    assert '".p12"' in content


def test_client_trust_export_requires_ca_certificate():
    content = _read(CLIENT_TRUST_EXPORT)

    assert '$_.Oid.Value -eq "2.5.29.19"' in content
    assert "$basicConstraints.CertificateAuthority" in content


def test_client_trust_export_checks_certificate_validity():
    content = _read(CLIENT_TRUST_EXPORT)

    assert "$rootCertificate.NotBefore -gt $now" in content
    assert "$rootCertificate.NotAfter -le $now" in content


def test_client_trust_export_generates_sha256_verification():
    content = _read(CLIENT_TRUST_EXPORT)

    assert "Get-FileHash" in content
    assert "-Algorithm SHA256" in content
    assert "[System.Security.Cryptography.SHA256]::Create()" in content
    assert '"SHA256SUMS.txt"' in content
    assert '"Certificate SHA-256 fingerprint: ' '$certificateFingerprint"' in content


def test_client_trust_export_is_read_only_for_standard_users():
    content = _read(CLIENT_TRUST_EXPORT)

    assert '"/inheritance:r"' in content
    assert '"*S-1-5-18:(OI)(CI)F"' in content
    assert '"*S-1-5-32-544:(OI)(CI)F"' in content
    assert '"*S-1-5-32-545:(OI)(CI)RX"' in content


def test_production_installer_requires_client_trust_export_script():
    content = _read(PRODUCTION_INSTALLER)

    assert (
        '"deployment\\windows\\networking\\'
        'Export-CareQFlowClientTrust.ps1"' in content
    )


def test_installer_exports_client_trust_for_networked_modes():
    content = _read(INSTALLER_WRAPPER)

    assert "$resolvedNetworkMode -in @(" in content
    assert '"SecureLan",' in content
    assert '"Tailscale"' in content
    assert '"Install",' in content
    assert '"Upgrade",' in content
    assert '"Repair"' in content
    assert "Export-CareQFlowClientTrust.ps1" in content


def test_client_trust_onboarding_supports_tailscale():
    content = _read(CLIENT_TRUST_EXPORT)

    assert '"CareQFlow Client Onboarding"' in content
    assert (
        '"- Tailscale access is limited by the configured '
        'tailnet access policy."' in content
    )


def test_client_trust_export_runs_after_post_install_health():
    content = _read(INSTALLER_WRAPPER)

    health_index = content.rfind("Assert-PostInstallationHealth")
    export_index = content.rfind("Export-CareQFlowClientTrust.ps1")

    assert health_index != -1
    assert export_index != -1
    assert health_index < export_index


def test_installer_runs_client_trust_export_in_current_process():
    content = _read(INSTALLER_WRAPPER)

    export_index = content.rfind("Export-CareQFlowClientTrust.ps1")
    export_block = content[export_index:]

    assert "& $clientTrustExportScript" in export_block
    assert "-DataDirectory $DataDirectory" in export_block
    assert "-ApplicationOrigin $ApplicationOrigin" in export_block

    assert (
        "& powershell.exe"
        not in export_block.split(
            '"Post-installation validation completed successfully."',
            maxsplit=1,
        )[0]
    )


def test_installer_logs_client_trust_export_output():
    content = _read(INSTALLER_WRAPPER)

    export_index = content.rfind("Export-CareQFlowClientTrust.ps1")
    export_block = content[export_index:]

    assert "*>&1" in export_block
    assert "Tee-Object" in export_block
    assert "-FilePath $logPath" in export_block


def test_client_trust_onboarding_uses_execution_policy_bypass():
    content = _read(CLIENT_TRUST_EXPORT)

    assert "'   powershell.exe -NoProfile -ExecutionPolicy Bypass '" in content
    assert "'-File \".\\Install-CareQFlowClientTrust.ps1\" '" in content


def test_client_trust_onboarding_passes_application_origin():
    content = _read(CLIENT_TRUST_EXPORT)

    assert "'-ApplicationOrigin \"'" in content
    assert "$normalizedApplicationOrigin" in content


def test_client_trust_onboarding_includes_verified_fingerprint():
    content = _read(CLIENT_TRUST_EXPORT)

    assert "'-ExpectedFingerprint \"'" in content
    assert "$certificateFingerprint" in content


def test_client_trust_onboarding_documents_friendly_hostname():
    content = _read(CLIENT_TRUST_EXPORT)

    assert '"Friendly client URL:"' in content
    assert '"https://careqflow.local"' in content
    assert '"The server IP URL also remains available:"' in content
