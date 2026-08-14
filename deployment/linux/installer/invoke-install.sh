#!/usr/bin/env bash

set -Eeuo pipefail

MODE="${1:-}"

INSTALL_DIRECTORY="${INSTALL_DIRECTORY:-/opt/carequeue}"
DATA_DIRECTORY="${DATA_DIRECTORY:-/var/lib/carequeue}"
CONFIG_DIRECTORY="${CONFIG_DIRECTORY:-/etc/carequeue}"
LOG_DIRECTORY="${LOG_DIRECTORY:-/var/log/carequeue}"

SCRIPT_DIRECTORY="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
    pwd
)"

LINUX_DEPLOYMENT_DIRECTORY="$(
    cd -- "${SCRIPT_DIRECTORY}/.." >/dev/null 2>&1
    pwd
)"

INSTALL_SCRIPT="${LINUX_DEPLOYMENT_DIRECTORY}/install-production.sh"
UNINSTALL_SCRIPT="${LINUX_DEPLOYMENT_DIRECTORY}/uninstall-production.sh"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail "CareQueue setup must be run as root."
    fi
}

normalize_mode() {
    MODE="$(
        printf '%s' "${MODE}" |
            tr '[:upper:]' '[:lower:]'
    )"

    case "${MODE}" in
        install|upgrade|repair|uninstall)
            ;;
        *)
            fail "Usage: $0 {install|upgrade|repair|uninstall}"
            ;;
    esac
}

installation_exists() {
    [[ -d "${INSTALL_DIRECTORY}/backend" ]] \
        && [[ -f "${CONFIG_DIRECTORY}/carequeue.env" ]]
}

validate_mode() {
    case "${MODE}" in
        install)
            if installation_exists; then
                fail "CareQueue is already installed. Use upgrade or repair."
            fi
            ;;

        upgrade|repair)
            if ! installation_exists; then
                fail "CareQueue is not currently installed. Use install."
            fi
            ;;

        uninstall)
            if ! installation_exists; then
                fail "CareQueue is not currently installed."
            fi
            ;;
    esac
}

prepare_logging() {
    local installer_log_directory
    local timestamp

    installer_log_directory="${LOG_DIRECTORY}/installer"

    mkdir -p "${installer_log_directory}"
    chmod 0750 "${LOG_DIRECTORY}"
    chmod 0750 "${installer_log_directory}"

    timestamp="$(date -u '+%Y%m%d-%H%M%S')"

    LOG_PATH="$(
        printf \
            '%s/CareQueue-%s-%s.log' \
            "${installer_log_directory}" \
            "${MODE}" \
            "${timestamp}"
    )"

    touch "${LOG_PATH}"
    chmod 0640 "${LOG_PATH}"

    exec > >(tee -a "${LOG_PATH}") 2>&1
}

print_header() {
    printf 'CareQueue Linux Installer\n'
    printf 'Mode: %s\n' "${MODE}"
    printf 'Started UTC: %s\n' "$(date -u --iso-8601=seconds)"
    printf 'Install directory: %s\n' "${INSTALL_DIRECTORY}"
    printf 'Data directory: %s\n' "${DATA_DIRECTORY}"
    printf 'Configuration directory: %s\n' "${CONFIG_DIRECTORY}"
    printf 'Log: %s\n\n' "${LOG_PATH}"
}

run_install_operation() {
    if [[ ! -f "${INSTALL_SCRIPT}" ]]; then
        fail "CareQueue production install script was not found: ${INSTALL_SCRIPT}"
    fi

    bash "${INSTALL_SCRIPT}"
}

run_uninstall_operation() {
    if [[ ! -f "${UNINSTALL_SCRIPT}" ]]; then
        fail "CareQueue production uninstall script was not found: ${UNINSTALL_SCRIPT}"
    fi

    bash "${UNINSTALL_SCRIPT}"
}

run_initial_admin_setup() {
    local admin_setup_script

    admin_setup_script="${INSTALL_DIRECTORY}/deployment/linux/CareQueue-AdminSetup.sh"

    if [[ ! -f "${admin_setup_script}" ]]; then
        fail "CareQueue admin setup script was not installed."
    fi

    bash "${admin_setup_script}"
}

main() {
    require_root
    normalize_mode
    validate_mode
    prepare_logging
    print_header

    case "${MODE}" in
        install)
            run_install_operation
            run_initial_admin_setup
            ;;

        upgrade)
            printf 'Upgrading CareQueue while preserving configuration and data...\n'
            run_install_operation
            ;;

        repair)
            printf 'Repairing CareQueue while preserving configuration and data...\n'
            run_install_operation
            ;;

        uninstall)
            run_uninstall_operation
            ;;
    esac

    printf '\n'
    printf 'CareQueue %s completed successfully.\n' "${MODE}"
    printf 'Completed UTC: %s\n' "$(date -u --iso-8601=seconds)"
    printf 'Log: %s\n' "${LOG_PATH}"
}

main "$@"