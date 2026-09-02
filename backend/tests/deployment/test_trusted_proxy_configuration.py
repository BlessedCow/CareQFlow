from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

WINDOWS_RUN_API = PROJECT_ROOT / "deployment" / "windows" / "run-api.ps1"
LINUX_API_SERVICE = (
    PROJECT_ROOT / "deployment" / "linux" / "systemd" / "carequeue-api.service"
)

WINDOWS_API_SERVICE = PROJECT_ROOT / "deployment" / "windows" / "CareQueueApi.xml"

WINDOWS_INSTALLER = (
    PROJECT_ROOT / "deployment" / "windows" / "installer" / "invoke-install.ps1"
)

WINDOWS_PRODUCTION_INSTALLER = (
    PROJECT_ROOT / "deployment" / "windows" / "install-production.ps1"
)

LINUX_PRODUCTION_INSTALLER = (
    PROJECT_ROOT / "deployment" / "linux" / "install-production.sh"
)

WINDOWS_CADDYFILE = PROJECT_ROOT / "deployment" / "windows" / "Caddyfile"

LINUX_CADDYFILE = PROJECT_ROOT / "deployment" / "linux" / "Caddyfile"

WINDOWS_ADMIN_SETUP = (
    PROJECT_ROOT / "deployment" / "windows" / "CareQueue-AdminSetup.ps1"
)

LINUX_ADMIN_SETUP = PROJECT_ROOT / "deployment" / "linux" / "CareQFlow-AdminSetup.sh"


def test_windows_api_trusts_forwarded_headers_only_from_loopback():
    content = WINDOWS_RUN_API.read_text(encoding="utf-8")

    assert "--proxy-headers" in content
    assert '--forwarded-allow-ips "127.0.0.1"' in content

    assert '--forwarded-allow-ips "*"' not in content
    assert "--forwarded-allow-ips 0.0.0.0/0" not in content


def test_linux_api_trusts_forwarded_headers_only_from_loopback():
    content = LINUX_API_SERVICE.read_text(encoding="utf-8")

    assert "--proxy-headers" in content
    assert "--forwarded-allow-ips 127.0.0.1" in content

    assert "--forwarded-allow-ips *" not in content
    assert "--forwarded-allow-ips 0.0.0.0/0" not in content


def test_windows_api_defaults_to_loopback():
    content = WINDOWS_RUN_API.read_text(encoding="utf-8")

    assert '[string]$HostAddress = "127.0.0.1"' in content
    assert "--host $HostAddress" in content


def test_windows_api_rejects_non_loopback_bind_addresses():
    content = WINDOWS_RUN_API.read_text(encoding="utf-8")

    assert '$HostAddress -notin @("127.0.0.1", "::1", "localhost")' in content
    assert "CareQFlow production API must bind only to loopback" in content


def test_windows_service_does_not_override_api_host():
    content = WINDOWS_API_SERVICE.read_text(encoding="utf-8")

    assert "-HostAddress" not in content


def test_linux_api_binds_only_to_loopback():
    content = LINUX_API_SERVICE.read_text(encoding="utf-8")

    assert "--host 127.0.0.1" in content
    assert "--host 0.0.0.0" not in content


def test_windows_installer_uses_trusted_production_data_root():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "AUTHSTATUS_PRODUCTION_DATA_ROOT=$DataDirectory" in content
    assert "AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=true" not in content
    assert "AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=true" not in content


def test_linux_installer_uses_trusted_production_data_root():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "AUTHSTATUS_PRODUCTION_DATA_ROOT=${DATA_DIRECTORY}" in content
    assert "AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=true" not in content
    assert "AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=true" not in content


def test_windows_installer_generates_secrets_with_cryptographic_rng():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "RandomNumberGenerator]::Create()" in content
    assert "New-FernetKey" in content
    assert "New-RandomSecret -ByteCount 48" in content


def test_windows_installer_generates_independent_encryption_keys():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "$fieldEncryptionKey = New-FernetKey" in content
    assert "$backupEncryptionKey = New-FernetKey" in content
    assert "$fieldEncryptionKey -eq $backupEncryptionKey" in content
    assert "Generated encryption keys must be independent." in content


def test_linux_installer_generates_secrets_with_cryptographic_rng():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "secrets.token_bytes(32)" in content
    assert "secrets.token_bytes(48)" in content
    assert "generate_fernet_key" in content
    assert "generate_random_secret" in content


def test_linux_installer_generates_independent_encryption_keys():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert 'field_encryption_key="$(generate_fernet_key)"' in content
    assert 'backup_encryption_key="$(generate_fernet_key)"' in content
    assert 'sqlcipher_key="$(generate_random_secret)"' in content
    assert '"${field_encryption_key}" == "${backup_encryption_key}"' in content
    assert "Generated encryption keys must be independent." in content


def test_linux_installer_restricts_production_environment_file():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "umask 0077" in content
    assert 'chown root:"${CAREQUEUE_GROUP}" "${environment_file}"' in content
    assert 'chmod 0640 "${environment_file}"' in content


def test_linux_installer_restricts_configuration_directory():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert '"${CONFIG_DIRECTORY}"' in content
    assert "-m 0750" in content


def test_linux_installer_migrates_legacy_path_configuration():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "^AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=" in content
    assert "^AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=" in content
    assert "^AUTHSTATUS_PRODUCTION_DATA_ROOT=" in content

    assert "'AUTHSTATUS_PRODUCTION_DATA_ROOT=%s\\n'" in content
    assert '"${DATA_DIRECTORY}"' in content

    assert "Production path configuration migrated to the trusted data root." in content


def test_linux_installer_migrates_legacy_default_application_origin():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    environment_function = content.split(
        "create_environment_file() {",
        maxsplit=1,
    )[
        1
    ].split("\n}", maxsplit=1,)[0]

    assert '-v application_origin="${APPLICATION_ORIGIN}"' in environment_function
    assert (
        '$0 == "AUTHSTATUS_CORS_ORIGINS=[\\"https://carequeue.local\\"]"'
        in environment_function
    )
    assert (
        'printf "AUTHSTATUS_CORS_ORIGINS=[\\"%s\\"]\\n", application_origin'
        in environment_function
    )


def test_linux_environment_migration_does_not_replace_custom_origins():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    environment_function = content.split(
        "create_environment_file() {",
        maxsplit=1,
    )[
        1
    ].split("\n}", maxsplit=1,)[0]

    assert "/^AUTHSTATUS_CORS_ORIGINS=/" not in environment_function


def test_linux_installer_validates_application_origin_before_installation():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "validate_application_origin()" in content
    assert 'parsed.scheme.lower() != "https"' in content
    assert "not parsed.hostname" in content
    assert "parsed.username is not None" in content
    assert "parsed.password is not None" in content
    assert 'parsed.path not in {"", "/"}' in content
    assert "parsed.query or parsed.fragment" in content

    assert (
        "validate_application_origin"
        in content.split(
            "detect_distribution",
            maxsplit=1,
        )[0]
    )


def test_linux_environment_migration_uses_restrictive_umask():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    environment_function = content.split(
        "create_environment_file() {",
        maxsplit=1,
    )[
        1
    ].split("\n}", maxsplit=1,)[0]

    assert environment_function.index("umask 0077") < (
        environment_function.index('if [[ -f "${environment_file}" ]]')
    )


def test_linux_environment_migration_does_not_depend_on_grep_matches():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    environment_function = content.split(
        "create_environment_file() {",
        maxsplit=1,
    )[
        1
    ].split("\n}", maxsplit=1,)[0]

    assert "awk \\" in environment_function
    assert "grep -Ev" not in environment_function


def test_windows_installer_disables_runtime_acl_inheritance():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "/inheritance:r" in content
    assert '"SYSTEM:(OI)(CI)F"' in content
    assert '"BUILTIN\\Administrators:(OI)(CI)F"' in content


def test_windows_installer_does_not_grant_broad_runtime_access():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "Everyone:(OI)(CI)" not in content
    assert "BUILTIN\\Users:(OI)(CI)" not in content
    assert "Authenticated Users:(OI)(CI)" not in content


def test_windows_service_does_not_pass_secrets_as_arguments():
    content = WINDOWS_API_SERVICE.read_text(encoding="utf-8")

    assert "AUTHSTATUS_ENCRYPTION_KEY=" not in content
    assert "AUTHSTATUS_SQLCIPHER_KEY=" not in content
    assert "AUTHSTATUS_BACKUP_ENCRYPTION_KEY=" not in content


def test_windows_installer_migrates_legacy_path_configuration():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "^AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=" in content
    assert "^AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=" in content
    assert "^AUTHSTATUS_PRODUCTION_DATA_ROOT=" in content

    assert '"AUTHSTATUS_PRODUCTION_DATA_ROOT=$DataDirectory"' in content

    assert "Production path configuration was migrated to the " in content
    assert "trusted data root." in content


def test_windows_installer_validates_application_origin():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "[Uri]$ApplicationOrigin" in content
    assert "$applicationUri.IsAbsoluteUri" in content
    assert '$applicationUri.Scheme -ne "https"' in content
    assert "-not $applicationUri.Host" in content
    assert "$applicationUri.UserInfo" in content
    assert '$applicationUri.AbsolutePath -ne "/"' in content
    assert "$applicationUri.Query" in content
    assert "$applicationUri.Fragment" in content


def test_windows_installer_normalizes_application_origin():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    assert "[System.UriPartial]::Authority" in content
    assert ".TrimEnd(" in content


def test_linux_service_loads_secrets_from_environment_file():
    content = LINUX_API_SERVICE.read_text(encoding="utf-8")

    assert "EnvironmentFile=/etc/carequeue/carequeue.env" in content

    assert "AUTHSTATUS_ENCRYPTION_KEY=" not in content
    assert "AUTHSTATUS_SQLCIPHER_KEY=" not in content
    assert "AUTHSTATUS_BACKUP_ENCRYPTION_KEY=" not in content


def test_windows_installer_does_not_log_generated_secrets():
    content = WINDOWS_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    forbidden_output = (
        "Write-Host $fieldEncryptionKey",
        "Write-Host $backupEncryptionKey",
        "Write-Host $sqlCipherKey",
        "Write-Output $fieldEncryptionKey",
        "Write-Output $backupEncryptionKey",
        "Write-Output $sqlCipherKey",
    )

    for output in forbidden_output:
        assert output not in content


def test_windows_admin_setup_uses_application_host_for_loopback_requests():
    content = WINDOWS_ADMIN_SETUP.read_text(encoding="utf-8")

    assert "$applicationUri = [Uri]$ApplicationUrl" in content
    assert "$trustedHostHeader = $applicationUri.Authority" in content

    assert "-HostHeader $trustedHostHeader" in content
    assert "Host = $HostHeader" in content
    assert "Host = $trustedHostHeader" in content


def test_linux_admin_setup_uses_application_host_for_loopback_requests():
    content = LINUX_ADMIN_SETUP.read_text(encoding="utf-8")

    assert "APPLICATION_ORIGIN" in content
    assert "127.0.0.1:8000" in content


def test_linux_installer_does_not_log_generated_secrets():
    content = LINUX_PRODUCTION_INSTALLER.read_text(encoding="utf-8")

    forbidden_output = (
        'printf "%s" "${field_encryption_key}"',
        'printf "%s" "${backup_encryption_key}"',
        'printf "%s" "${sqlcipher_key}"',
        'echo "${field_encryption_key}"',
        'echo "${backup_encryption_key}"',
        'echo "${sqlcipher_key}"',
    )

    for output in forbidden_output:
        assert output not in content


def assert_security_headers(content: str) -> None:
    required_headers = (
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
    )

    for header in required_headers:
        assert header in content

    assert "-Server" in content


def test_windows_caddyfile_sets_required_security_headers():
    content = WINDOWS_CADDYFILE.read_text(encoding="utf-8")

    assert_security_headers(content)


def test_linux_caddyfile_sets_required_security_headers():
    content = LINUX_CADDYFILE.read_text(encoding="utf-8")

    assert_security_headers(content)
