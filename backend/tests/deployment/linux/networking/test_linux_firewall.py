from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]

NETWORK_ACCESS_SCRIPT = (
    PROJECT_ROOT
    / "deployment"
    / "linux"
    / "networking"
    / "Set-CareQFlowNetworkAccess.sh"
)

PRODUCTION_INSTALLER = PROJECT_ROOT / "deployment" / "linux" / "install-production.sh"

UNINSTALLER = PROJECT_ROOT / "deployment" / "linux" / "uninstall-production.sh"

PAYLOAD_BUILDER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "build-payload.ps1"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_secure_lan_requires_active_firewall():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert "detect_active_firewall" in content
    assert "SecureLan requires an active UFW or firewalld firewall." in content


def test_secure_lan_supports_ufw_and_firewalld():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert 'FIREWALL_MANAGER="ufw"' in content
    assert 'FIREWALL_MANAGER="firewalld"' in content


def test_secure_lan_resolves_selected_address_to_local_interface():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert "ip -o -4 addr show scope global" in content
    assert '"${cidr%%/*}" == "${application_ip}"' in content
    assert "The selected Secure LAN address is not assigned " in content


def test_secure_lan_derives_local_subnet():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert "ipaddress.ip_interface(" in content
    assert ").network" in content


def test_ufw_rule_allows_only_https_from_selected_subnet():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert 'from "${SECURE_LAN_SUBNET}"' in content
    assert "port 443" in content
    assert "proto tcp" in content
    assert "CareQFlow Secure LAN HTTPS" in content


def test_firewalld_rule_allows_only_https_from_selected_subnet():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert 'source address="%s"' in content
    assert 'port port="443"' in content
    assert 'protocol="tcp"' in content


def test_firewall_configuration_never_opens_fastapi_port():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert "port 8000" not in content
    assert 'port="8000"' not in content


def test_network_access_state_is_persisted_for_cleanup():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert "CAREQUEUE_NETWORK_ACCESS_SCHEMA=1" in content
    assert "CAREQUEUE_FIREWALL_MANAGER=" in content
    assert "CAREQUEUE_FIREWALL_SUBNET=" in content
    assert "CAREQUEUE_FIREWALL_ZONE=" in content


def test_network_state_writer_preserves_caddy_directory_access():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert "-g carequeue \\\n        -m 0710 \\" in content
    assert 'chown root:root "${STATE_FILE}"' in content
    assert 'chmod 0640 "${STATE_FILE}"' in content


def test_local_only_removes_previous_managed_rule():
    content = _read(NETWORK_ACCESS_SCRIPT)

    remove_index = content.index("remove_previous_managed_rule")
    local_only_index = content.index('if [[ "${NETWORK_MODE}" == "LocalOnly" ]]')

    assert remove_index < local_only_index


def test_installer_configures_firewall_before_services_start():
    content = _read(PRODUCTION_INSTALLER)

    network_index = content.index("configure_network_access\n")
    services_index = content.index("start_services\n")

    assert network_index < services_index


def test_installer_requires_network_access_script():
    content = _read(PRODUCTION_INSTALLER)

    assert '"deployment/linux/networking/' 'Set-CareQFlowNetworkAccess.sh"' in content


def test_payload_requires_network_access_script():
    content = _read(PAYLOAD_BUILDER)

    assert (
        '"deployment\\linux\\networking\\' 'Set-CareQFlowNetworkAccess.sh"' in content
    )


def test_uninstall_removes_managed_network_access():
    content = _read(UNINSTALLER)

    assert "remove_network_access" in content
    assert "--network-mode LocalOnly" in content

    network_index = content.index("remove_network_access\n")
    services_index = content.index("stop_services\n")

    assert network_index < services_index
