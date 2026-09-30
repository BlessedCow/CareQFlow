from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]

CLIENT_TRUST_INSTALLER = (
    PROJECT_ROOT
    / "deployment"
    / "windows"
    / "networking"
    / "Install-CareQFlowClientTrust.ps1"
)

CLIENT_TRUST_EXPORT = (
    PROJECT_ROOT
    / "deployment"
    / "windows"
    / "networking"
    / "Export-CareQFlowClientTrust.ps1"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_client_trust_installer_requires_administrator():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "Test-Administrator" in content
    assert "requires Administrator privileges." in content


def test_client_trust_installer_requires_expected_sha256_fingerprint():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "[string]$ExpectedFingerprint" in content
    assert "Get-CertificateSha256Fingerprint" in content
    assert "$Certificate.RawData" in content
    assert "SHA256" in content


def test_client_trust_installer_rejects_fingerprint_mismatch():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert ("$actualFingerprint -cne " "$normalizedExpectedFingerprint") in content
    assert "Do not trust this " in content
    assert '"certificate."' in content


def test_client_trust_installer_rejects_private_key_material():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "$certificate.HasPrivateKey" in content
    assert "contains private key material." in content


def test_client_trust_installer_requires_ca_certificate():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert '$_.Oid.Value -eq "2.5.29.19"' in content
    assert "$basicConstraints.CertificateAuthority" in content


def test_client_trust_installer_checks_certificate_signing_usage():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert '$_.Oid.Value -eq "2.5.29.15"' in content
    assert "X509KeyUsageFlags" in content
    assert "KeyCertSign" in content


def test_client_trust_installer_checks_certificate_validity():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "$certificate.NotBefore -gt $now" in content
    assert "$certificate.NotAfter -le $now" in content


def test_client_trust_installer_uses_local_machine_root_store():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert '"Cert:\\LocalMachine\\Root"' in content
    assert "Import-Certificate" in content


def test_client_trust_installer_is_idempotent():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "$existingCertificate" in content
    assert "is already " in content
    assert "trusted on this computer." in content


def test_client_trust_installer_verifies_import():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "$installedCertificate" in content
    assert "could not be verified " in content
    assert "in the Windows trusted root store" in content


def test_client_trust_export_includes_windows_installer():
    content = _read(CLIENT_TRUST_EXPORT)

    assert '"Install-CareQFlowClientTrust.ps1"' in content
    assert "$clientInstallerSource" in content
    assert "$clientInstallerDestination" in content


def test_client_trust_export_blocks_private_key_file_types_recursively():
    content = _read(CLIENT_TRUST_EXPORT)

    assert "-Recurse" in content
    assert '".key"' in content
    assert '".pfx"' in content
    assert '".p12"' in content
    assert '".pem"' in content


def test_client_trust_installer_accepts_optional_application_origin():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "[string]$ApplicationOrigin" in content
    assert "Set-CareQFlowClientHostname" in content


def test_client_hostname_requires_https_private_ipv4_origin():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert '$applicationUri.Scheme -ne "https"' in content
    assert "[System.UriHostNameType]::IPv4" in content
    assert "$bytes[0] -eq 10" in content
    assert "$bytes[0] -eq 172" in content
    assert "$bytes[0] -eq 192" in content
    assert "$bytes[1] -eq 168" in content


def test_client_hostname_updates_windows_hosts_file():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert '"System32\\drivers\\etc\\hosts"' in content
    assert '$hostname = "careqflow.local"' in content
    assert "$replacementLine" in content
    assert "Set-Content" in content


def test_client_hostname_mapping_is_replaced_instead_of_duplicated():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "$mappingAdded = $false" in content
    assert "-contains $hostname" in content
    assert "continue" in content


def test_client_hostname_flushes_dns_cache():
    content = _read(CLIENT_TRUST_INSTALLER)

    assert "Clear-DnsClientCache" in content


def test_existing_certificate_does_not_exit_before_hostname_configuration():
    content = _read(CLIENT_TRUST_INSTALLER)

    existing_branch = content.split(
        "if ($existingCertificate) {",
        maxsplit=1,
    )[
        1
    ].split("else {", maxsplit=1,)[0]

    assert "exit 0" not in existing_branch
    assert "Set-CareQFlowClientHostname" in content
