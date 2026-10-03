from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[5]

LINUX_PRODUCTION_INSTALLER = (
    PROJECT_ROOT / "deployment" / "linux" / "install-production.sh"
)

LINUX_INSTALLER_WRAPPER = (
    PROJECT_ROOT / "deployment" / "linux" / "installer" / "invoke-install.sh"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _shell_function(content: str, name: str) -> str:
    marker = f"{name}() {{"

    assert marker in content

    return content.split(marker, maxsplit=1)[1].split(
        "\n}",
        maxsplit=1,
    )[0]


def test_linux_network_mode_defaults_to_local_only():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    assert 'NETWORK_MODE="${NETWORK_MODE:-LocalOnly}"' in content
    assert 'LOCAL_APPLICATION_ORIGIN="https://careqflow.local"' in content


def test_linux_network_mode_accepts_only_supported_modes():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_network_mode",
    )

    assert "LocalOnly|SecureLan|Tailscale" in function
    assert "Network mode must be LocalOnly, SecureLan, or Tailscale." in function


def test_linux_secure_lan_requires_https_origin():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_secure_lan_origin",
    )

    assert 'if [[ "${NETWORK_MODE}" != "SecureLan" ]]' in function
    assert 'parsed.scheme.lower() != "https"' in function


def test_linux_tailscale_requires_https_origin():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_tailscale_origin",
    )

    assert 'if [[ "${NETWORK_MODE}" != "Tailscale" ]]' in function
    assert 'parsed.scheme.lower() != "https"' in function


def test_linux_tailscale_accepts_only_cgnat_network():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_tailscale_origin",
    )

    assert 'ipaddress.IPv4Network("100.64.0.0/10")' in function
    assert "if address not in tailscale_network:" in function


def test_linux_tailscale_requires_standard_https_port():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_tailscale_origin",
    )

    assert "if port not in {None, 443}:" in function


def test_linux_secure_lan_requires_ipv4():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_secure_lan_origin",
    )

    assert "ipaddress.IPv4Address(parsed.hostname)" in function
    assert "ipaddress.AddressValueError" in function


def test_linux_secure_lan_accepts_only_rfc1918_networks():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_secure_lan_origin",
    )

    assert 'ipaddress.IPv4Network("10.0.0.0/8")' in function
    assert 'ipaddress.IPv4Network("172.16.0.0/12")' in function
    assert 'ipaddress.IPv4Network("192.168.0.0/16")' in function


def test_linux_secure_lan_requires_standard_https_port():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_secure_lan_origin",
    )

    assert "if port not in {None, 443}:" in function


def test_linux_installation_state_persists_network_mode():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "write_installation_state",
    )

    assert "CAREQUEUE_NETWORK_MODE=${NETWORK_MODE}" in function
    assert "CAREQUEUE_APPLICATION_ORIGIN=${APPLICATION_ORIGIN}" in function


def test_linux_network_validation_runs_before_installation():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    main_function = _shell_function(
        content,
        "main",
    )

    network_mode_index = main_function.index(
        "validate_network_mode",
    )
    application_origin_index = main_function.index(
        "validate_application_origin",
    )
    secure_lan_index = main_function.index(
        "validate_secure_lan_origin",
    )
    dependency_index = main_function.index(
        "install_system_dependencies",
    )

    assert network_mode_index < application_origin_index
    assert application_origin_index < secure_lan_index
    assert secure_lan_index < dependency_index


def test_linux_wrapper_accepts_network_mode_options():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "parse_network_options",
    )

    assert "--network-mode" in function
    assert "--application-origin" in function


def test_linux_wrapper_normalizes_supported_network_modes():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "normalize_requested_network_mode",
    )

    assert 'REQUESTED_NETWORK_MODE="LocalOnly"' in function
    assert 'REQUESTED_NETWORK_MODE="SecureLan"' in function
    assert 'REQUESTED_NETWORK_MODE="Tailscale"' in function
    assert "Network mode must be LocalOnly, SecureLan, or Tailscale." in function


def test_linux_new_install_defaults_to_local_only():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_network_configuration",
    )

    assert 'RESOLVED_NETWORK_MODE="${REQUESTED_NETWORK_MODE:-LocalOnly}"' in function
    assert 'RESOLVED_APPLICATION_ORIGIN="${LOCAL_APPLICATION_ORIGIN}"' in function


def test_linux_secure_lan_install_requires_selected_origin():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_network_configuration",
    )

    assert 'if [[ -z "${REQUESTED_APPLICATION_ORIGIN}" ]]' in function
    assert "SecureLan mode requires --application-origin" in function


def test_linux_tailscale_install_requires_selected_origin():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_network_configuration",
    )

    assert 'RESOLVED_NETWORK_MODE}" == "Tailscale"' in function
    assert "Tailscale mode requires --application-origin" in function
    assert "the CareQFlow host Tailscale IPv4 address." in function


def test_linux_upgrade_and_repair_read_installed_network_state():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_network_configuration",
    )

    assert '"CAREQUEUE_NETWORK_MODE"' in function
    assert '"CAREQUEUE_APPLICATION_ORIGIN"' in function


def test_linux_legacy_install_defaults_to_local_only():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_network_configuration",
    )

    assert 'installed_network_mode="LocalOnly"' in function
    assert 'installed_application_origin="${LOCAL_APPLICATION_ORIGIN}"' in function


def test_linux_networked_upgrade_preserves_existing_origin():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_network_configuration",
    )

    assert '[[ "${installed_network_mode}" == "SecureLan" ]]' in function
    assert '[[ "${installed_network_mode}" == "Tailscale" ]]' in function
    assert 'RESOLVED_APPLICATION_ORIGIN="${installed_application_origin%/}"' in function


def test_linux_switch_to_tailscale_requires_new_origin():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "resolve_network_configuration",
    )

    assert 'if [[ "${RESOLVED_NETWORK_MODE}" == "Tailscale" ]]' in function
    assert "Tailscale mode requires --application-origin using" in function


def test_linux_wrapper_passes_network_configuration_to_installer():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "run_install_operation",
    )

    assert 'NETWORK_MODE="${RESOLVED_NETWORK_MODE}"' in function
    assert 'APPLICATION_ORIGIN="${RESOLVED_APPLICATION_ORIGIN}"' in function
    assert 'bash "${INSTALL_SCRIPT}"' in function


def test_linux_admin_setup_receives_resolved_application_origin():
    content = _read(LINUX_INSTALLER_WRAPPER)

    function = _shell_function(
        content,
        "run_initial_admin_setup",
    )

    assert 'APPLICATION_ORIGIN="${RESOLVED_APPLICATION_ORIGIN}"' in function
    assert 'bash "${admin_setup_script}"' in function


def test_linux_network_configuration_resolves_before_install_operations():
    content = _read(LINUX_INSTALLER_WRAPPER)

    main_function = _shell_function(
        content,
        "main",
    )

    parse_index = main_function.index(
        'parse_network_options "$@"',
    )
    normalize_index = main_function.index(
        "normalize_requested_network_mode",
    )
    resolve_index = main_function.index(
        "resolve_network_configuration",
    )
    backup_index = main_function.index(
        "create_verified_pre_upgrade_backup",
    )

    assert parse_index < normalize_index
    assert normalize_index < resolve_index
    assert resolve_index < backup_index


def test_linux_cors_origins_are_local_only_by_default():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "build_cors_origins",
    )

    assert 'if [[ "${NETWORK_MODE}" != "LocalOnly" ]]' in function
    assert '"${LOCAL_APPLICATION_ORIGIN}"' in function
    assert '"${APPLICATION_ORIGIN%/}"' in function


def test_linux_existing_managed_cors_origins_are_migrated():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "create_environment_file",
    )

    assert 'AUTHSTATUS_CORS_ORIGINS=[\\"https://carequeue.local\\"]' in function
    assert 'AUTHSTATUS_CORS_ORIGINS=[\\"https://careqflow.local\\"]' in function
    assert "previous_managed_cors_origins" in function
    assert 'current_cors="${cors_origins}"' in function


def test_linux_caddy_uses_local_hostname_and_network_origin():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "install_caddy_configuration",
    )

    assert 'caddy_site_addresses="careqflow.local"' in function
    assert 'if [[ "${NETWORK_MODE}" != "LocalOnly" ]]' in function
    assert 'application_authority="${APPLICATION_ORIGIN#https://}"' in function
    assert (
        'caddy_site_addresses="${caddy_site_addresses}, '
        '${application_authority}"' in function
    )


def test_linux_caddy_configuration_permissions_allow_service_read_access():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "install_caddy_configuration",
    )

    assert 'chown root:carequeue "${CONFIG_DIRECTORY}"' in function
    assert 'chmod 0710 "${CONFIG_DIRECTORY}"' in function

    assert ("-g carequeue \\\n" "        -m 0640 \\") in function


def test_linux_caddy_template_is_rewritten_before_validation():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "install_caddy_configuration",
    )

    rewrite_index = function.index(
        'expected = "careqflow.local {"',
    )
    validation_index = function.index(
        "caddy validate",
    )

    assert rewrite_index < validation_index


def test_linux_networked_modes_health_check_both_origins():
    content = _read(LINUX_PRODUCTION_INSTALLER)

    function = _shell_function(
        content,
        "validate_post_installation_health",
    )

    assert 'application_origin="${APPLICATION_ORIGIN%/}"' in function
    assert 'local_application_origin="${LOCAL_APPLICATION_ORIGIN%/}"' in function
    assert 'if [[ "${NETWORK_MODE}" != "LocalOnly" ]]' in function
    assert '"${application_origin}/api/health/live"' in function
    assert '"${local_application_origin}/api/health/live"' in function


def test_linux_fastapi_is_not_changed_to_network_listener():
    caddy_content = _read(PROJECT_ROOT / "deployment" / "linux" / "Caddyfile")

    assert "reverse_proxy 127.0.0.1:8000" in caddy_content
    assert "reverse_proxy 0.0.0.0:8000" not in caddy_content
