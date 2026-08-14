#!/usr/bin/env bash

set -Eeuo pipefail

INSTALL_DIRECTORY="${INSTALL_DIRECTORY:-/opt/carequeue}"
DATA_DIRECTORY="${DATA_DIRECTORY:-/var/lib/carequeue}"
CONFIG_DIRECTORY="${CONFIG_DIRECTORY:-/etc/carequeue}"
LOG_DIRECTORY="${LOG_DIRECTORY:-/var/log/carequeue}"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail "CareQueue uninstall must be run as root."
    fi
}

stop_services() {
    printf 'Stopping CareQueue services...\n'

    systemctl disable --now carequeue-backup.timer \
        2>/dev/null || true

    systemctl disable --now carequeue-caddy.service \
        2>/dev/null || true

    systemctl disable --now carequeue-api.service \
        2>/dev/null || true
}

remove_systemd_units() {
    printf 'Removing CareQueue systemd units...\n'

    rm -f \
        /etc/systemd/system/carequeue-api.service \
        /etc/systemd/system/carequeue-backup.service \
        /etc/systemd/system/carequeue-backup.timer \
        /etc/systemd/system/carequeue-caddy.service

    systemctl daemon-reload
    systemctl reset-failed
}

remove_application_files() {
    printf 'Removing CareQueue application files...\n'

    rm -rf "${INSTALL_DIRECTORY}"
}

remove_local_hostname() {
    local hosts_file
    local temporary_file

    hosts_file="/etc/hosts"
    temporary_file="$(mktemp)"

    awk '
        $0 !~ /# CareQueue$/ {
            print
        }
    ' "${hosts_file}" > "${temporary_file}"

    cat "${temporary_file}" > "${hosts_file}"

    rm -f "${temporary_file}"
}

print_preserved_data() {
    printf '\n'
    printf 'CareQueue application files and services were removed.\n'
    printf '\n'
    printf 'The following data was preserved intentionally:\n'
    printf '  Configuration: %s\n' "${CONFIG_DIRECTORY}"
    printf '  Runtime data:  %s\n' "${DATA_DIRECTORY}"
    printf '  Logs:          %s\n' "${LOG_DIRECTORY}"
    printf '\n'
    printf 'A normal uninstall does not delete the CareQueue database or encryption keys.\n'
}

main() {
    require_root
    stop_services
    remove_systemd_units
    remove_application_files
    remove_local_hostname
    print_preserved_data
}

main "$@"