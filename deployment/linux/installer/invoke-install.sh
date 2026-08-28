#!/usr/bin/env bash

set -Eeuo pipefail

MODE="${1:-}"

INSTALL_DIRECTORY="${INSTALL_DIRECTORY:-/opt/carequeue}"
DATA_DIRECTORY="${DATA_DIRECTORY:-/var/lib/carequeue}"
CONFIG_DIRECTORY="${CONFIG_DIRECTORY:-/etc/carequeue}"
LOG_DIRECTORY="${LOG_DIRECTORY:-/var/log/carequeue}"
BACKUP_DIRECTORY="${BACKUP_DIRECTORY:-${DATA_DIRECTORY}/backups}"

SCRIPT_DIRECTORY="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
    pwd
)"

LINUX_DEPLOYMENT_DIRECTORY="$(
    cd -- "${SCRIPT_DIRECTORY}/.." >/dev/null 2>&1
    pwd
)"

PACKAGE_ROOT_DIRECTORY="$(
    cd -- "${LINUX_DEPLOYMENT_DIRECTORY}/../.." >/dev/null 2>&1
    pwd
)"

RELEASE_METADATA_FILE="${PACKAGE_ROOT_DIRECTORY}/carequeue-release.env"
INSTALL_STATE_FILE="${CONFIG_DIRECTORY}/install-state.env"

INCOMING_VERSION=""
INSTALLED_VERSION=""
PRE_UPGRADE_BACKUP_PATH=""
UPGRADE_RECOVERY_DIRECTORY="${DATA_DIRECTORY}/recovery/upgrades"
UPGRADE_RECOVERY_RECORD=""

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

read_env_value() {
    local file_path="$1"
    local key="$2"

    awk -F= \
        -v requested_key="${key}" \
        '$1 == requested_key {
            sub(/^[^=]*=/, "", $0)
            print $0
            exit
        }' \
        "${file_path}"
}

validate_version_string() {
    local version="$1"

    [[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

compare_versions() {
    local left_version="$1"
    local right_version="$2"

    local left_major
    local left_minor
    local left_patch
    local right_major
    local right_minor
    local right_patch

    IFS='.' read -r \
        left_major \
        left_minor \
        left_patch \
        <<< "${left_version}"

    IFS='.' read -r \
        right_major \
        right_minor \
        right_patch \
        <<< "${right_version}"

    if (( 10#${left_major} > 10#${right_major} )); then
        printf '1\n'
        return
    fi

    if (( 10#${left_major} < 10#${right_major} )); then
        printf '%s\n' '-1'
        return
    fi

    if (( 10#${left_minor} > 10#${right_minor} )); then
        printf '1\n'
        return
    fi

    if (( 10#${left_minor} < 10#${right_minor} )); then
        printf '%s\n' '-1'
        return
    fi

    if (( 10#${left_patch} > 10#${right_patch} )); then
        printf '1\n'
        return
    fi

    if (( 10#${left_patch} < 10#${right_patch} )); then
        printf '%s\n' '-1'
        return
    fi

    printf '0\n'
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

validate_upgrade_version() {
    local comparison

    if [[ "${MODE}" != "upgrade" ]]; then
        return
    fi

    if [[ ! -f "${RELEASE_METADATA_FILE}" ]]; then
        fail \
            "CareQueue release metadata was not found: " \
            "${RELEASE_METADATA_FILE}"
    fi

    INCOMING_VERSION="$(
        read_env_value \
            "${RELEASE_METADATA_FILE}" \
            "CAREQUEUE_APP_VERSION"
    )"

    if ! validate_version_string "${INCOMING_VERSION}"; then
        fail \
            "Incoming CareQueue package has an invalid application version: " \
            "${INCOMING_VERSION:-missing}"
    fi

    if [[ ! -f "${INSTALL_STATE_FILE}" ]]; then
        printf '%s\n' \
            'Installed CareQueue version metadata is unavailable. Continuing legacy upgrade validation.'
        return
    fi

    INSTALLED_VERSION="$(
        read_env_value \
            "${INSTALL_STATE_FILE}" \
            "CAREQUEUE_INSTALLED_VERSION"
    )"

    if [[ -z "${INSTALLED_VERSION}" ]]; then
        printf '%s\n' \
            'Installed CareQueue version metadata is unavailable. Continuing legacy upgrade validation.'
        return
    fi

    if ! validate_version_string "${INSTALLED_VERSION}"; then
        fail \
            "Installed CareQueue version metadata is invalid: " \
            "${INSTALLED_VERSION}"
    fi

    comparison="$(
        compare_versions \
            "${INCOMING_VERSION}" \
            "${INSTALLED_VERSION}"
    )"

    case "${comparison}" in
        1)
            printf \
                'Validated CareQueue upgrade path: %s -> %s\n' \
                "${INSTALLED_VERSION}" \
                "${INCOMING_VERSION}"
            ;;

        0)
            fail \
                "CareQueue ${INCOMING_VERSION} is already installed. " \
                "Use repair instead of upgrade."
            ;;

        -1)
            fail \
                "CareQueue downgrade refused: installed version " \
                "${INSTALLED_VERSION}, incoming version ${INCOMING_VERSION}."
            ;;

        *)
            fail "Unable to compare CareQueue release versions."
            ;;
    esac
}

create_verified_pre_upgrade_backup() {
    local backup_service
    local backup_script
    local backup_marker
    local backup_path

    if [[ "${MODE}" != "upgrade" ]]; then
        return
    fi

    backup_service="/etc/systemd/system/carequeue-backup.service"
    backup_script="${INSTALL_DIRECTORY}/backend/scripts/create_encrypted_backup.py"

    if [[ ! -f "${backup_service}" ]]; then
        fail \
            "CareQueue upgrade requires the installed backup service: " \
            "${backup_service}"
    fi

    if [[ ! -f "${backup_script}" ]]; then
        fail \
            "CareQueue upgrade requires the installed backup script: " \
            "${backup_script}"
    fi

    if [[ ! -f "${CONFIG_DIRECTORY}/carequeue.env" ]]; then
        fail \
            "CareQueue upgrade requires the production configuration: " \
            "${CONFIG_DIRECTORY}/carequeue.env"
    fi

    mkdir -p "${BACKUP_DIRECTORY}"

    backup_marker="$(
        mktemp \
            "${BACKUP_DIRECTORY}/.carequeue-pre-upgrade-marker.XXXXXX"
    )"

    chmod 0600 "${backup_marker}"

    printf 'Creating and verifying pre-upgrade encrypted backup...\n'

    if ! systemctl start carequeue-backup.service; then
        rm -f "${backup_marker}"

        fail \
            "Pre-upgrade backup creation or verification failed. " \
            "The CareQueue application has not been replaced."
    fi

    backup_path="$(
        find "${BACKUP_DIRECTORY}" \
            -maxdepth 1 \
            -type f \
            -name '*.db.enc' \
            -newer "${backup_marker}" \
            -printf '%T@ %p\n' |
            sort -nr |
            head -n 1 |
            cut -d' ' -f2-
    )"

    rm -f "${backup_marker}"

    if [[ -z "${backup_path}" ]]; then
        fail \
            "The CareQueue backup service completed but no new " \
            "pre-upgrade backup could be identified. " \
            "The CareQueue application has not been replaced."
    fi

    if [[ ! -s "${backup_path}" ]]; then
        fail \
            "The pre-upgrade backup is missing or empty: " \
            "${backup_path}"
    fi

    PRE_UPGRADE_BACKUP_PATH="${backup_path}"

    printf 'Verified pre-upgrade backup: %s\n' "${PRE_UPGRADE_BACKUP_PATH}"
}

write_upgrade_recovery_record() {
    local attempted_at

    if [[ "${MODE}" != "upgrade" ]]; then
        return
    fi

    if [[ -z "${PRE_UPGRADE_BACKUP_PATH}" ]]; then
        fail \
            "Cannot create upgrade recovery state because the " \
            "verified pre-upgrade backup path is unavailable."
    fi

    mkdir -p "${UPGRADE_RECOVERY_DIRECTORY}"
    chmod 0750 "${UPGRADE_RECOVERY_DIRECTORY}"

    attempted_at="$(date -u --iso-8601=seconds)"

    UPGRADE_RECOVERY_RECORD="$(
        printf \
            '%s/upgrade-%s-to-%s.env' \
            "${UPGRADE_RECOVERY_DIRECTORY}" \
            "${INSTALLED_VERSION:-legacy}" \
            "${INCOMING_VERSION}"
    )"

    cat > "${UPGRADE_RECOVERY_RECORD}" <<EOF
CAREQUEUE_UPGRADE_RECOVERY_SCHEMA=1
CAREQUEUE_PREVIOUS_VERSION=${INSTALLED_VERSION:-unknown}
CAREQUEUE_INCOMING_VERSION=${INCOMING_VERSION}
CAREQUEUE_PRE_UPGRADE_BACKUP=${PRE_UPGRADE_BACKUP_PATH}
CAREQUEUE_INSTALLER_LOG=${LOG_PATH}
CAREQUEUE_UPGRADE_ATTEMPTED_AT=${attempted_at}
CAREQUEUE_UPGRADE_STATUS=pending
EOF

    chmod 0640 "${UPGRADE_RECOVERY_RECORD}"

    printf \
        'Upgrade recovery record created: %s\n' \
        "${UPGRADE_RECOVERY_RECORD}"
}

update_upgrade_recovery_status() {
    local status="$1"
    local temporary_record

    if [[ "${MODE}" != "upgrade" ]]; then
        return
    fi

    if [[ -z "${UPGRADE_RECOVERY_RECORD}" ]] \
        || [[ ! -f "${UPGRADE_RECOVERY_RECORD}" ]]; then
        return
    fi

    temporary_record="${UPGRADE_RECOVERY_RECORD}.tmp"

    awk \
        -v replacement_status="${status}" \
        '
        /^CAREQUEUE_UPGRADE_STATUS=/ {
            print "CAREQUEUE_UPGRADE_STATUS=" replacement_status
            next
        }
        {
            print
        }
        ' \
        "${UPGRADE_RECOVERY_RECORD}" \
        > "${temporary_record}"

    chmod 0640 "${temporary_record}"
    mv -f "${temporary_record}" "${UPGRADE_RECOVERY_RECORD}"
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
    validate_upgrade_version
    prepare_logging
    print_header
    create_verified_pre_upgrade_backup
    write_upgrade_recovery_record

    case "${MODE}" in
        install)
            run_install_operation
            run_initial_admin_setup
            ;;

        upgrade)
            printf 'Upgrading CareQueue while preserving configuration and data...\n'

            if run_install_operation; then
                update_upgrade_recovery_status "completed"
            else
                update_upgrade_recovery_status "failed"

                fail \
                    "CareQueue upgrade failed. Recovery information was preserved at: " \
                    "${UPGRADE_RECOVERY_RECORD}"
            fi
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