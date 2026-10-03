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


def test_network_access_accepts_tailscale_mode():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert "LocalOnly|SecureLan|Tailscale" in content
    assert "Network mode must be LocalOnly, SecureLan, or Tailscale." in content


def test_tailscale_requires_installed_client():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert "command -v tailscale" in content
    assert "Tailscale mode requires the Tailscale client to be installed." in content


def test_tailscale_requires_cgnat_ipv4_origin():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert 'ipaddress.IPv4Network("100.64.0.0/10")' in content
    assert "if address not in tailnet:" in content
    assert (
        "Tailscale mode requires an HTTPS origin using a "
        "Tailscale IPv4 address." in content
    )


def test_tailscale_origin_must_match_local_tailscale_address():
    content = _read(NETWORK_ACCESS_SCRIPT)

    assert '["tailscale", "ip", "-4"]' in content
    assert '"${application_ip}" != "${tailscale_ip}"' in content
    assert "The selected Tailscale address is not assigned to this host." in content


def test_tailscale_does_not_create_careqflow_lan_firewall_rule():
    content = _read(NETWORK_ACCESS_SCRIPT)

    tailscale_branch = content.split(
        'if [[ "${NETWORK_MODE}" == "Tailscale" ]]; then',
        maxsplit=1,
    )[1].split("return", maxsplit=1,)[0]

    assert "resolve_tailscale_ipv4" in tailscale_branch
    assert "write_state" in tailscale_branch
    assert "detect_active_firewall" not in tailscale_branch
    assert "configure_ufw" not in tailscale_branch
    assert "configure_firewalld" not in tailscale_branch


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


def test_tailscale_lookup_has_timeout():
    content = _read(NETWORK_ACCESS_SCRIPT)

    function = content.split(
        "resolve_tailscale_ipv4() {",
        maxsplit=1,
    )[1].split(
        "\n}",
        maxsplit=1,
    )[0]

    assert "subprocess.run(" in function
    assert '["tailscale", "ip", "-4"]' in function
    assert "timeout=10" in function
    assert "except subprocess.TimeoutExpired:" in function
    assert "raise SystemExit(124)" in function
    assert '"${tailscale_status}" -eq 124' in function
    assert "Tailscale did not respond within 10 seconds." in function
