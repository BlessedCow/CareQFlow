#!/usr/bin/env bash

set -Eeuo pipefail

APPLICATION_ORIGIN="${APPLICATION_ORIGIN:-https://carequeue.local}"

INSTALL_DIRECTORY="${INSTALL_DIRECTORY:-/opt/carequeue}"
DATA_DIRECTORY="${DATA_DIRECTORY:-/var/lib/carequeue}"
CONFIG_DIRECTORY="${CONFIG_DIRECTORY:-/etc/carequeue}"
LOG_DIRECTORY="${LOG_DIRECTORY:-/var/log/carequeue}"

CAREQUEUE_USER="${CAREQUEUE_USER:-carequeue}"
CAREQUEUE_GROUP="${CAREQUEUE_GROUP:-carequeue}"

SCRIPT_DIRECTORY="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
    pwd
)"

SOURCE_DIRECTORY="$(
    cd -- "${SCRIPT_DIRECTORY}/../.." >/dev/null 2>&1
    pwd
)"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail "CareQueue installation must be run as root."
    fi
}

validate_application_origin() {
    if ! python3 - "${APPLICATION_ORIGIN}" <<'PY'
import sys
from urllib.parse import urlsplit

origin = sys.argv[1].strip()

try:
    parsed = urlsplit(origin)
    port = parsed.port
except ValueError:
    raise SystemExit(1)

if parsed.scheme.lower() != "https":
    raise SystemExit(1)

if not parsed.hostname:
    raise SystemExit(1)

if parsed.username is not None or parsed.password is not None:
    raise SystemExit(1)

if parsed.path not in {"", "/"}:
    raise SystemExit(1)

if parsed.query or parsed.fragment:
    raise SystemExit(1)

if port is not None and not 1 <= port <= 65535:
    raise SystemExit(1)
PY
    then
        fail \
            "Application origin must be an absolute HTTPS origin " \
            "containing only a hostname and optional port."
    fi
}

detect_distribution() {
    if [[ ! -f /etc/os-release ]]; then
        fail "Unable to identify the Linux distribution."
    fi

    # shellcheck disable=SC1091
    source /etc/os-release

    DISTRO_ID="${ID:-unknown}"
    DISTRO_VERSION="${VERSION_ID:-unknown}"

    case "${DISTRO_ID}" in
        ubuntu|debian|linuxmint|fedora)
            ;;
        *)
            fail "Unsupported Linux distribution: ${DISTRO_ID} ${DISTRO_VERSION}."
            ;;
    esac

    printf 'Detected Linux distribution: %s %s\n' \
        "${DISTRO_ID}" \
        "${DISTRO_VERSION}"
}

install_system_dependencies() {
    printf 'Installing CareQueue system dependencies...\n'

    case "${DISTRO_ID}" in
        ubuntu|debian|linuxmint)
            export DEBIAN_FRONTEND=noninteractive

            apt-get update

            apt-get install -y \
                ca-certificates \
                curl \
                libsqlcipher-dev \
                python3 \
                python3-dev \
                python3-pip \
                python3-venv \
                build-essential
            ;;
        fedora)
            dnf install -y \
                ca-certificates \
                curl \
                sqlcipher-devel \
                python3 \
                python3-devel \
                python3-pip \
                gcc \
                gcc-c++ \
                make
            ;;
        *)
            fail "No dependency installer is configured for ${DISTRO_ID}."
            ;;
    esac
}

ensure_service_account() {
    if getent group "${CAREQUEUE_GROUP}" >/dev/null 2>&1; then
        printf 'CareQueue group already exists.\n'
    else
        groupadd --system "${CAREQUEUE_GROUP}"
    fi

    if id "${CAREQUEUE_USER}" >/dev/null 2>&1; then
        printf 'CareQueue service account already exists.\n'
        return
    fi

    local nologin_shell

    nologin_shell="$(command -v nologin || true)"

    if [[ -z "${nologin_shell}" ]]; then
        nologin_shell="/usr/sbin/nologin"
    fi

    useradd \
        --system \
        --gid "${CAREQUEUE_GROUP}" \
        --home-dir "${DATA_DIRECTORY}" \
        --no-create-home \
        --shell "${nologin_shell}" \
        "${CAREQUEUE_USER}"
}

create_directories() {
    printf 'Creating CareQueue directories...\n'

    install \
        -d \
        -o root \
        -g "${CAREQUEUE_GROUP}" \
        -m 0750 \
        "${INSTALL_DIRECTORY}"

    install \
        -d \
        -o "${CAREQUEUE_USER}" \
        -g "${CAREQUEUE_GROUP}" \
        -m 0750 \
        "${DATA_DIRECTORY}" \
        "${DATA_DIRECTORY}/data" \
        "${DATA_DIRECTORY}/backups" \
        "${DATA_DIRECTORY}/restores" \
        "${DATA_DIRECTORY}/recovery" \
        "${DATA_DIRECTORY}/caddy" \
        "${DATA_DIRECTORY}/caddy/data" \
        "${DATA_DIRECTORY}/caddy/config"

    install \
        -d \
        -o root \
        -g "${CAREQUEUE_GROUP}" \
        -m 0750 \
        "${CONFIG_DIRECTORY}"

    install \
        -d \
        -o "${CAREQUEUE_USER}" \
        -g "${CAREQUEUE_GROUP}" \
        -m 0750 \
        "${LOG_DIRECTORY}"
}

copy_application_files() {
    printf 'Installing CareQueue application files...\n'

    rm -rf \
        "${INSTALL_DIRECTORY}/backend" \
        "${INSTALL_DIRECTORY}/frontend" \
        "${INSTALL_DIRECTORY}/deployment"

    mkdir -p \
        "${INSTALL_DIRECTORY}/backend" \
        "${INSTALL_DIRECTORY}/frontend" \
        "${INSTALL_DIRECTORY}/deployment"

    cp -a --no-preserve=context \
        "${SOURCE_DIRECTORY}/backend/." \
        "${INSTALL_DIRECTORY}/backend/"

    cp -a --no-preserve=context \
        "${SOURCE_DIRECTORY}/deployment/." \
        "${INSTALL_DIRECTORY}/deployment/"

    if [[ -d "${SOURCE_DIRECTORY}/frontend/dist" ]]; then
        mkdir -p "${INSTALL_DIRECTORY}/frontend/dist"

        cp -a --no-preserve=context \
            "${SOURCE_DIRECTORY}/frontend/dist/." \
            "${INSTALL_DIRECTORY}/frontend/dist/"
    else
        fail "A prebuilt production frontend was not found at frontend/dist."
    fi

    chown -R root:"${CAREQUEUE_GROUP}" "${INSTALL_DIRECTORY}"
    chmod -R go-w "${INSTALL_DIRECTORY}"

    if command -v restorecon >/dev/null 2>&1; then
        restorecon -RF "${INSTALL_DIRECTORY}"
    fi
}

create_python_environment() {
    local backend_directory
    local virtual_environment

    backend_directory="${INSTALL_DIRECTORY}/backend"
    virtual_environment="${backend_directory}/.venv"

    printf 'Creating CareQueue Python environment...\n'

    rm -rf "${virtual_environment}"

    python3 -m venv "${virtual_environment}"

    "${virtual_environment}/bin/python" \
        -m pip install \
        --upgrade \
        pip \
        setuptools \
        wheel

    printf 'Installing CareQueue backend dependencies...\n'

    "${virtual_environment}/bin/python" \
        -m pip install \
        --requirement "${backend_directory}/requirements.txt"

    printf 'Validating the CareQueue backend...\n'

    (
        cd "${backend_directory}"

        "${virtual_environment}/bin/python" \
            -c 'import authstatus_api.main'
    )

    chown -R root:"${CAREQUEUE_GROUP}" "${virtual_environment}"
    chmod -R go-w "${virtual_environment}"
}

generate_fernet_key() {
    python3 - <<'PY'
import base64
import secrets

print(
    base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode("ascii")
)
PY
}

generate_random_secret() {
    python3 - <<'PY'
import base64
import secrets

print(
    base64.urlsafe_b64encode(
        secrets.token_bytes(48)
    ).decode("ascii").rstrip("=")
)
PY
}

create_environment_file() {
    umask 0077

    local environment_file
    local database_path
    local backup_directory
    local restore_directory
    local field_encryption_key
    local backup_encryption_key
    local sqlcipher_key
    local cors_origins

    environment_file="${CONFIG_DIRECTORY}/carequeue.env"

    database_path="${DATA_DIRECTORY}/data/auth_tracker.sqlcipher.db"
    backup_directory="${DATA_DIRECTORY}/backups"
    restore_directory="${DATA_DIRECTORY}/restores"

    if [[ -f "${environment_file}" ]]; then
        printf '%s\n' \
            'Existing CareQueue production configuration found. Preserving it.'

        local migrated_environment_file

        migrated_environment_file="${environment_file}.tmp"

        awk '
            !/^AUTHSTATUS_ALLOW_UNSAFE_DATABASE_PATH=/ &&
            !/^AUTHSTATUS_ALLOW_UNSAFE_STORAGE_PATHS=/ &&
            !/^AUTHSTATUS_PRODUCTION_DATA_ROOT=/
        ' "${environment_file}" > "${migrated_environment_file}"

        printf 'AUTHSTATUS_PRODUCTION_DATA_ROOT=%s\n' \
            "${DATA_DIRECTORY}" \
            >> "${migrated_environment_file}"

        mv \
            "${migrated_environment_file}" \
            "${environment_file}"

        chown root:"${CAREQUEUE_GROUP}" "${environment_file}"
        chmod 0640 "${environment_file}"

        printf '%s\n' \
            'Production path configuration migrated to the trusted data root.'

        return
    fi

    printf 'Generating independent CareQueue encryption keys...\n'

    field_encryption_key="$(generate_fernet_key)"
    backup_encryption_key="$(generate_fernet_key)"
    sqlcipher_key="$(generate_random_secret)"

    if [[ "${field_encryption_key}" == "${backup_encryption_key}" ]]; then
        fail "Generated encryption keys must be independent."
    fi

    cors_origins="[\"${APPLICATION_ORIGIN}\"]"

    cat > "${environment_file}" <<EOF
AUTHSTATUS_APP_ENVIRONMENT=production
AUTHSTATUS_ENCRYPTION_KEY=${field_encryption_key}
AUTHSTATUS_SQLCIPHER_KEY=${sqlcipher_key}
AUTHSTATUS_BACKUP_ENCRYPTION_KEY=${backup_encryption_key}
AUTHSTATUS_DATABASE_PATH=${database_path}
AUTHSTATUS_DATABASE_ENCRYPTION=sqlcipher
AUTHSTATUS_PRODUCTION_DATA_ROOT=${DATA_DIRECTORY}
AUTHSTATUS_BACKUP_DIRECTORY=${backup_directory}
AUTHSTATUS_BACKUP_RETENTION_DAYS=90
AUTHSTATUS_BACKUP_MINIMUM_COUNT=5
AUTHSTATUS_RESTORE_DIRECTORY=${restore_directory}
AUTHSTATUS_CORS_ORIGINS=${cors_origins}
AUTHSTATUS_SESSION_COOKIE_SECURE=true
AUTHSTATUS_SESSION_COOKIE_NAME=carequeue_session
AUTHSTATUS_CSRF_COOKIE_NAME=carequeue_csrf
AUTHSTATUS_CSRF_HEADER_NAME=X-CSRF-Token
EOF

    chown root:"${CAREQUEUE_GROUP}" "${environment_file}"
    chmod 0640 "${environment_file}"

    printf 'CareQueue production configuration created.\n'
}

write_installation_state() {
    local state_file

    state_file="${CONFIG_DIRECTORY}/install-state.env"

    cat > "${state_file}" <<EOF
CAREQUEUE_INSTALL_DIRECTORY=${INSTALL_DIRECTORY}
CAREQUEUE_DATA_DIRECTORY=${DATA_DIRECTORY}
CAREQUEUE_CONFIG_DIRECTORY=${CONFIG_DIRECTORY}
CAREQUEUE_APPLICATION_ORIGIN=${APPLICATION_ORIGIN}
CAREQUEUE_HOSTS_ENTRY_MANAGED=true
EOF

    chown root:"${CAREQUEUE_GROUP}" "${state_file}"
    chmod 0640 "${state_file}"
}

install_systemd_units() {
    printf 'Installing CareQueue systemd units...\n'

    install \
        -o root \
        -g root \
        -m 0644 \
        "${SOURCE_DIRECTORY}/deployment/linux/systemd/carequeue-api.service" \
        "/etc/systemd/system/carequeue-api.service"

    install \
        -o root \
        -g root \
        -m 0644 \
        "${SOURCE_DIRECTORY}/deployment/linux/systemd/carequeue-backup.service" \
        "/etc/systemd/system/carequeue-backup.service"

    install \
        -o root \
        -g root \
        -m 0644 \
        "${SOURCE_DIRECTORY}/deployment/linux/systemd/carequeue-backup.timer" \
        "/etc/systemd/system/carequeue-backup.timer"

    install \
        -o root \
        -g root \
        -m 0644 \
        "${SOURCE_DIRECTORY}/deployment/linux/systemd/carequeue-caddy.service" \
        "/etc/systemd/system/carequeue-caddy.service"

    systemctl daemon-reload
}

install_caddy() {
    printf 'Installing Caddy...\n'

    if command -v caddy >/dev/null 2>&1; then
        printf 'Caddy is already installed.\n'
        return
    fi

    case "${DISTRO_ID}" in
        ubuntu|debian|linuxmint)
            apt-get install -y \
                debian-keyring \
                debian-archive-keyring \
                apt-transport-https \
                curl \
                gnupg

            curl -1sLf \
                'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
                | gpg --dearmor \
                -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

            curl -1sLf \
                'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
                > /etc/apt/sources.list.d/caddy-stable.list

            chmod o+r \
                /usr/share/keyrings/caddy-stable-archive-keyring.gpg

            chmod o+r \
                /etc/apt/sources.list.d/caddy-stable.list

            apt-get update
            apt-get install -y caddy
            ;;
        fedora)
            dnf install -y \
                'dnf-command(copr)'

            dnf copr enable -y @caddy/caddy

            dnf install -y caddy
            ;;
        *)
            fail "No Caddy installer is configured for ${DISTRO_ID}."
            ;;
    esac
}

disable_default_caddy_service() {
    printf 'Ensuring the default Caddy service is not running...\n'

    if systemctl list-unit-files caddy.service \
        >/dev/null 2>&1
    then
        systemctl disable --now caddy.service \
            2>/dev/null || true
    fi
}

install_caddy_configuration() {
    printf 'Installing CareQueue Caddy configuration...\n'

    install \
        -o root \
        -g root \
        -m 0644 \
        "${SOURCE_DIRECTORY}/deployment/linux/Caddyfile" \
        "${CONFIG_DIRECTORY}/Caddyfile"

    caddy validate \
        --config "${CONFIG_DIRECTORY}/Caddyfile" \
        --adapter caddyfile
}

configure_local_hostname() {
    local hosts_file
    local hostname_pattern

    hosts_file="/etc/hosts"
    hostname_pattern='(^|[[:space:]])carequeue\.local([[:space:]]|$)'

    if grep -Eq "${hostname_pattern}" "${hosts_file}"; then
        printf 'carequeue.local is already present in /etc/hosts.\n'
        return
    fi

    printf 'Adding carequeue.local to /etc/hosts...\n'

    printf '\n127.0.0.1 carequeue.local # CareQueue\n' \
        >> "${hosts_file}"
}

start_services() {
    printf 'Starting CareQueue services...\n'

    systemctl enable carequeue-api.service
    systemctl enable carequeue-caddy.service
    systemctl enable carequeue-backup.timer

    systemctl restart carequeue-api.service
    systemctl restart carequeue-caddy.service
    systemctl start carequeue-backup.timer
}

trust_caddy_root_certificate() {
    printf 'Trusting the CareQueue Caddy root certificate...\n'

    local maximum_attempts
    local attempt

    maximum_attempts=30

    for ((attempt = 1; attempt <= maximum_attempts; attempt++)); do
        if XDG_DATA_HOME="${DATA_DIRECTORY}/caddy/data" \
            XDG_CONFIG_HOME="${DATA_DIRECTORY}/caddy/config" \
            caddy trust \
                --config "${CONFIG_DIRECTORY}/Caddyfile" \
                --adapter caddyfile
            then
            printf 'Caddy root certificate trusted successfully.\n'
            return
        fi

        if (( attempt < maximum_attempts )); then
            printf \
                'Caddy trust attempt %d of %d failed. Retrying...\n' \
                "${attempt}" \
                "${maximum_attempts}"

            sleep 1
        fi
    done

    fail "Unable to trust the CareQueue Caddy root certificate."
}

validate_services() {
    printf 'Validating CareQueue systemd services...\n'

    systemctl is-active --quiet carequeue-api.service \
        || fail "carequeue-api.service is not running."

    systemctl is-active --quiet carequeue-caddy.service \
        || fail "carequeue-caddy.service is not running."

    systemctl is-enabled --quiet carequeue-backup.timer \
        || fail "carequeue-backup.timer is not enabled."
}

validate_http_endpoint() {
    local name
    local url
    local maximum_attempts
    local attempt
    local response_code

    name="$1"
    url="$2"
    maximum_attempts="${3:-30}"

    for ((attempt = 1; attempt <= maximum_attempts; attempt++)); do
        response_code="$(
            curl \
                --silent \
                --show-error \
                --output /dev/null \
                --write-out '%{http_code}' \
                --connect-timeout 5 \
                --max-time 10 \
                "${url}" \
                || true
        )"

        if [[ "${response_code}" =~ ^2[0-9][0-9]$ ]] \
            || [[ "${response_code}" =~ ^3[0-9][0-9]$ ]]
        then
            printf \
                '%s validation succeeded with HTTP %s.\n' \
                "${name}" \
                "${response_code}"

            return
        fi

        printf \
            '%s validation failed at %s (attempt %d of %d, HTTP %s).\n' \
            "${name}" \
            "${url}" \
            "${attempt}" \
            "${maximum_attempts}" \
            "${response_code:-none}"

        if (( attempt < maximum_attempts )); then
            sleep 2
        fi
    done

    fail "${name} validation failed at ${url} after ${maximum_attempts} attempts."
}

validate_post_installation_health() {
    printf 'Running CareQueue post installation validation...\n'

    local application_origin

    application_origin="${APPLICATION_ORIGIN%/}"

    validate_services

    validate_http_endpoint \
        "HTTPS frontend" \
        "${application_origin}/"

    validate_http_endpoint \
        "API live health check" \
        "${application_origin}/api/health/live"

    validate_http_endpoint \
        "API readiness health check" \
        "${application_origin}/api/health/ready"

    printf 'CareQueue post installation validation completed successfully.\n'
}

validate_source() {
    local required_paths=(
        "backend/authstatus_api"
        "backend/scripts"
        "backend/requirements.txt"
        "frontend/dist/index.html"
        "deployment/linux/Caddyfile"
        "deployment/linux/CareQueue-AdminSetup.sh"
        "deployment/linux/systemd/carequeue-api.service"
        "deployment/linux/systemd/carequeue-backup.service"
        "deployment/linux/systemd/carequeue-backup.timer"
        "deployment/linux/systemd/carequeue-caddy.service"
    )

    local relative_path

    for relative_path in "${required_paths[@]}"; do
        if [[ ! -e "${SOURCE_DIRECTORY}/${relative_path}" ]]; then
            fail "Required CareQueue source was not found: ${relative_path}"
        fi
    done
}

main() {
    require_root
    validate_application_origin
    detect_distribution
    validate_source
    install_system_dependencies
    ensure_service_account
    create_directories
    copy_application_files
    create_python_environment
    create_environment_file
    write_installation_state
    install_systemd_units
    install_caddy
    disable_default_caddy_service
    install_caddy_configuration
    configure_local_hostname
    start_services
    trust_caddy_root_certificate
    validate_post_installation_health

    printf '\n'
    printf 'CareQueue Linux installation completed successfully.\n'
    printf 'Install directory: %s\n' "${INSTALL_DIRECTORY}"
    printf 'Data directory: %s\n' "${DATA_DIRECTORY}"
    printf 'Configuration directory: %s\n' "${CONFIG_DIRECTORY}"
}

main "$@"