from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]

CLIENT_INSTALLER = (
    PROJECT_ROOT
    / "deployment"
    / "linux"
    / "networking"
    / "Install-CareQFlowClientTrust.sh"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_linux_client_trust_requires_root():
    content = _read(CLIENT_INSTALLER)

    assert 'if [[ "${EUID}" -ne 0 ]]' in content
    assert "must be run as root" in content


def test_linux_client_trust_requires_expected_fingerprint():
    content = _read(CLIENT_INSTALLER)

    assert "--expected-fingerprint" in content
    assert "EXPECTED_FINGERPRINT" in content
    assert "^[0-9A-F]{64}$" in content


def test_linux_client_trust_verifies_sha256_fingerprint():
    content = _read(CLIENT_INSTALLER)

    assert "openssl x509" in content
    assert "-fingerprint" in content
    assert "-sha256" in content
    assert "The CareQFlow certificate SHA-256 fingerprint does not " in content
    assert "match the expected fingerprint. Do not trust this certificate." in content


def test_linux_client_trust_rejects_private_key_material():
    content = _read(CLIENT_INSTALLER)

    assert "PRIVATE KEY" in content
    assert "unexpectedly" in content


def test_linux_client_trust_requires_ca_certificate():
    content = _read(CLIENT_INSTALLER)

    assert "CA:TRUE" in content
    assert "certificate authority" in content


def test_linux_client_trust_supports_debian_trust_store():
    content = _read(CLIENT_INSTALLER)

    assert "update-ca-certificates" in content
    assert "/usr/local/share/ca-certificates/" "CareQFlow-Root-CA.crt" in content


def test_linux_client_trust_supports_update_ca_trust():
    content = _read(CLIENT_INSTALLER)

    assert "update-ca-trust" in content
    assert "/etc/pki/ca-trust/source/anchors/" "CareQFlow-Root-CA.crt" in content


def test_linux_client_hostname_requires_private_ipv4_origin():
    content = _read(CLIENT_INSTALLER)

    assert 'ipaddress.IPv4Network("10.0.0.0/8")' in content
    assert 'ipaddress.IPv4Network("172.16.0.0/12")' in content
    assert 'ipaddress.IPv4Network("192.168.0.0/16")' in content


def test_linux_client_hostname_updates_etc_hosts():
    content = _read(CLIENT_INSTALLER)

    assert 'hosts_file="/etc/hosts"' in content
    assert 'CAREQUEUE_HOSTNAME="careqflow.local"' in content
    assert 'f"{server_ip} {hostname} # CareQFlow"' in content


def test_linux_client_hostname_removes_previous_mapping():
    content = _read(CLIENT_INSTALLER)

    assert "if value != hostname" in content
    assert "remaining_hosts" in content


def test_linux_client_trust_keeps_ip_url_available():
    content = _read(CLIENT_INSTALLER)

    assert "Friendly URL: https://%s" in content
    assert "Server URL: %s" in content
