from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]

EXPORT_SCRIPT = (
    PROJECT_ROOT
    / "deployment"
    / "linux"
    / "networking"
    / "Export-CareQFlowClientTrust.sh"
)

CLIENT_INSTALLER = (
    PROJECT_ROOT
    / "deployment"
    / "linux"
    / "networking"
    / "Install-CareQFlowClientTrust.sh"
)

PRODUCTION_INSTALLER = PROJECT_ROOT / "deployment" / "linux" / "install-production.sh"

PAYLOAD_BUILDER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "build-payload.ps1"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_linux_client_trust_export_uses_caddy_public_root():
    content = _read(EXPORT_SCRIPT)

    assert "caddy/data/caddy/pki/authorities/local/root.crt" in content


def test_linux_client_trust_export_rejects_private_key_material():
    content = _read(EXPORT_SCRIPT)

    assert "PRIVATE KEY" in content
    assert "BEGIN .*PRIVATE KEY" in content
    assert "*.key" in content
    assert "*.pfx" in content
    assert "*.p12" in content
    assert "*.pem" in content


def test_linux_client_trust_export_validates_ca_certificate():
    content = _read(EXPORT_SCRIPT)

    assert "openssl x509" in content
    assert "CA:TRUE" in content
    assert "openssl verify" in content


def test_linux_client_trust_export_writes_fingerprint():
    content = _read(EXPORT_SCRIPT)

    assert "-fingerprint" in content
    assert "-sha256" in content
    assert "Certificate SHA-256 fingerprint:" in content


def test_linux_client_trust_export_includes_installer():
    content = _read(EXPORT_SCRIPT)

    assert "Install-CareQFlowClientTrust.sh" in content
    assert "CLIENT-ONBOARDING.txt" in content
    assert "SHA256SUMS.txt" in content


def test_linux_client_trust_onboarding_uses_selected_origin():
    content = _read(EXPORT_SCRIPT)

    assert '--application-origin "${APPLICATION_ORIGIN}"' in content
    assert "https://careqflow.local" in content


def test_linux_installer_exports_trust_for_networked_modes():
    content = _read(PRODUCTION_INSTALLER)

    assert "export_client_trust()" in content
    assert 'if [[ "${NETWORK_MODE}" == "LocalOnly" ]]' in content
    assert "CLIENT_TRUST_EXPORT_SCRIPT" in content


def test_linux_client_trust_export_accepts_tailscale_addresses():
    content = _read(EXPORT_SCRIPT)

    assert 'ipaddress.IPv4Network("100.64.0.0/10")' in content
    assert "supported_networks" in content


def test_linux_client_trust_installer_accepts_tailscale_addresses():
    content = _read(CLIENT_INSTALLER)

    assert 'ipaddress.IPv4Network("100.64.0.0/10")' in content
    assert "supported_networks" in content


def test_linux_client_trust_export_runs_after_caddy_trust():
    content = _read(PRODUCTION_INSTALLER)

    main_function = content.split(
        "main() {",
        maxsplit=1,
    )[1].split(
        "\n}",
        maxsplit=1,
    )[0]

    trust_index = main_function.index(
        "trust_caddy_root_certificate",
    )
    export_index = main_function.index(
        "export_client_trust",
    )
    health_index = main_function.index(
        "validate_post_installation_health",
    )

    assert trust_index < export_index
    assert export_index < health_index


def test_linux_payload_requires_client_trust_scripts():
    content = _read(PAYLOAD_BUILDER)

    assert (
        '"deployment\\linux\\networking\\' 'Export-CareQFlowClientTrust.sh"' in content
    )
    assert (
        '"deployment\\linux\\networking\\' 'Install-CareQFlowClientTrust.sh"' in content
    )


def test_linux_client_trust_installer_exists():
    assert CLIENT_INSTALLER.is_file()
