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
ROLLBACK_RECOVERY_RECORD=""
ROLLBACK_PREVIOUS_VERSION=""
ROLLBACK_INCOMING_VERSION=""
ROLLBACK_BACKUP_PATH=""
ROLLBACK_APPLICATION_ARCHIVE=""
ROLLBACK_APPLICATION_SHA256=""
ROLLBACK_APPLICATION_STAGING_DIRECTORY=""
ROLLBACK_APPLICATION_STAGING_ROOT=""
PRE_UPGRADE_APPLICATION_ARCHIVE=""
PRE_UPGRADE_APPLICATION_SHA256=""
UPGRADE_APPLICATION_RECOVERY_DIRECTORY="${DATA_DIRECTORY}/recovery/applications"
FAILED_APPLICATION_ARCHIVE=""
FAILED_APPLICATION_SHA256=""

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
        install|upgrade|repair|rollback|uninstall)
            ;;
        *)
            fail "Usage: $0 {install|upgrade|repair|rollback|uninstall}"
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

        upgrade|repair|rollback)
            if ! installation_exists; then
                fail "CareQueue is not currently installed. Use install."
            fi
            ;;

        uninstall)
            if ! installation_exists; then
                fail "CareQueue is not currently installed. Use install."
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

create_verified_pre_upgrade_application_archive() {
    local archive_name
    local checksum_path
    local calculated_checksum

    if [[ "${MODE}" != "upgrade" ]]; then
        return
    fi

    if [[ -z "${INSTALLED_VERSION}" ]]; then
        printf '%s\n' \
            "Installed version metadata is unavailable; application rollback payload will not be created for this legacy upgrade."
        return
    fi

    if ! validate_version_string "${INSTALLED_VERSION}"; then
        fail \
            "Cannot preserve the installed application because its version metadata is invalid: ${INSTALLED_VERSION}"
    fi

    if [[ ! -d "${INSTALL_DIRECTORY}/backend" ]] \
        || [[ ! -d "${INSTALL_DIRECTORY}/frontend" ]] \
        || [[ ! -d "${INSTALL_DIRECTORY}/deployment" ]]; then
        fail \
            "Cannot preserve the installed CareQueue application because required application directories are missing."
    fi

    mkdir -p "${UPGRADE_APPLICATION_RECOVERY_DIRECTORY}"
    chmod 0750 "${UPGRADE_APPLICATION_RECOVERY_DIRECTORY}"

    archive_name="$(
        printf \
            'carequeue-application-%s.tar.gz' \
            "${INSTALLED_VERSION}"
    )"

    PRE_UPGRADE_APPLICATION_ARCHIVE="${
        UPGRADE_APPLICATION_RECOVERY_DIRECTORY
    }/${archive_name}"

    checksum_path="${PRE_UPGRADE_APPLICATION_ARCHIVE}.sha256"

    printf \
        'Preserving installed CareQueue %s application payload...\n' \
        "${INSTALLED_VERSION}"

    rm -f \
        "${PRE_UPGRADE_APPLICATION_ARCHIVE}" \
        "${checksum_path}"

    tar \
        --create \
        --gzip \
        --file "${PRE_UPGRADE_APPLICATION_ARCHIVE}" \
        --directory "${INSTALL_DIRECTORY}" \
        --exclude='backend/.venv' \
        backend \
        frontend \
        deployment

    if [[ ! -s "${PRE_UPGRADE_APPLICATION_ARCHIVE}" ]]; then
        fail \
            "The pre-upgrade application archive was not created successfully."
    fi

    PRE_UPGRADE_APPLICATION_SHA256="$(
        sha256sum "${PRE_UPGRADE_APPLICATION_ARCHIVE}" |
            awk '{print $1}'
    )"

    if [[ ! "${PRE_UPGRADE_APPLICATION_SHA256}" =~ ^[0-9a-f]{64}$ ]]; then
        fail \
            "Unable to calculate the pre-upgrade application archive checksum."
    fi

    printf '%s  %s\n' \
        "${PRE_UPGRADE_APPLICATION_SHA256}" \
        "$(basename "${PRE_UPGRADE_APPLICATION_ARCHIVE}")" \
        > "${checksum_path}"

    chmod 0640 \
        "${PRE_UPGRADE_APPLICATION_ARCHIVE}" \
        "${checksum_path}"

    calculated_checksum="$(
        sha256sum "${PRE_UPGRADE_APPLICATION_ARCHIVE}" |
            awk '{print $1}'
    )"

    if [[ "${calculated_checksum}" != "${PRE_UPGRADE_APPLICATION_SHA256}" ]]; then
        fail \
            "Pre-upgrade application archive checksum verification failed."
    fi

    printf \
        'Verified pre-upgrade application payload: %s\n' \
        "${PRE_UPGRADE_APPLICATION_ARCHIVE}"

    printf \
        'Pre-upgrade application SHA256: %s\n' \
        "${PRE_UPGRADE_APPLICATION_SHA256}"
}

write_upgrade_recovery_record() {
    local attempted_at

    if [[ "${MODE}" != "upgrade" ]]; then
        return
    fi

    if [[ -z "${PRE_UPGRADE_BACKUP_PATH}" ]]; then
        fail \
            "Cannot create upgrade recovery state because the verified pre-upgrade backup path is unavailable."
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
CAREQUEUE_PRE_UPGRADE_APPLICATION=${PRE_UPGRADE_APPLICATION_ARCHIVE}
CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256=${PRE_UPGRADE_APPLICATION_SHA256}
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

update_rollback_recovery_status() {
    local status="$1"
    local temporary_record

    if [[ "${MODE}" != "rollback" ]]; then
        return
    fi

    if [[ -z "${ROLLBACK_RECOVERY_RECORD}" ]] \
        || [[ ! -f "${ROLLBACK_RECOVERY_RECORD}" ]]; then
        return
    fi

    temporary_record="${ROLLBACK_RECOVERY_RECORD}.tmp"

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
        "${ROLLBACK_RECOVERY_RECORD}" \
        > "${temporary_record}"

    chmod 0640 "${temporary_record}"
    mv -f "${temporary_record}" "${ROLLBACK_RECOVERY_RECORD}"
}

restore_previous_install_state_version() {
    local temporary_state

    if [[ "${MODE}" != "rollback" ]]; then
        return
    fi

    if [[ -z "${ROLLBACK_PREVIOUS_VERSION}" ]] \
        || [[ "${ROLLBACK_PREVIOUS_VERSION}" == "unknown" ]]; then
        printf '%s\n' \
            "Previous CareQueue version metadata is unavailable; installed version metadata was not changed."
        return
    fi

    if ! validate_version_string "${ROLLBACK_PREVIOUS_VERSION}"; then
        fail \
            "Cannot restore installed version metadata because the previous CareQueue version is invalid: ${ROLLBACK_PREVIOUS_VERSION}"
    fi

    if [[ ! -f "${INSTALL_STATE_FILE}" ]]; then
        fail \
            "Cannot restore installed version metadata because the installation state file is missing: ${INSTALL_STATE_FILE}"
    fi

    temporary_state="${INSTALL_STATE_FILE}.tmp"

    awk \
        -v restored_version="${ROLLBACK_PREVIOUS_VERSION}" \
        '
        /^CAREQUEUE_INSTALLED_VERSION=/ {
            print "CAREQUEUE_INSTALLED_VERSION=" restored_version
            found = 1
            next
        }
        {
            print
        }
        END {
            if (!found) {
                print "CAREQUEUE_INSTALLED_VERSION=" restored_version
            }
        }
        ' \
        "${INSTALL_STATE_FILE}" \
        > "${temporary_state}"

    chmod 0640 "${temporary_state}"
    mv -f "${temporary_state}" "${INSTALL_STATE_FILE}"

    printf \
        'Installed CareQueue version metadata restored to %s\n' \
        "${ROLLBACK_PREVIOUS_VERSION}"
}

resolve_failed_upgrade_recovery_record() {
    local calculated_application_sha256
    local record_path
    local record_status

    if [[ "${MODE}" != "rollback" ]]; then
        return
    fi

    if [[ ! -d "${UPGRADE_RECOVERY_DIRECTORY}" ]]; then
        fail \
            "No CareQueue upgrade recovery records are available."
    fi

    record_path="$(
        find "${UPGRADE_RECOVERY_DIRECTORY}" \
            -maxdepth 1 \
            -type f \
            -name 'upgrade-*.env' \
            -printf '%T@ %p\n' |
            sort -nr |
            cut -d' ' -f2- |
            while IFS= read -r candidate; do
                record_status="$(
                    read_env_value \
                        "${candidate}" \
                        "CAREQUEUE_UPGRADE_STATUS"
                )"

                if [[ "${record_status}" == "failed" ]]; then
                    printf '%s\n' "${candidate}"
                    break
                fi
            done
    )"

    if [[ -z "${record_path}" ]]; then
        fail \
            "No failed CareQueue upgrade recovery record was found."
    fi

    ROLLBACK_RECOVERY_RECORD="${record_path}"

    ROLLBACK_PREVIOUS_VERSION="$(
        read_env_value \
            "${ROLLBACK_RECOVERY_RECORD}" \
            "CAREQUEUE_PREVIOUS_VERSION"
    )"

    ROLLBACK_INCOMING_VERSION="$(
        read_env_value \
            "${ROLLBACK_RECOVERY_RECORD}" \
            "CAREQUEUE_INCOMING_VERSION"
    )"

    ROLLBACK_BACKUP_PATH="$(
        read_env_value \
            "${ROLLBACK_RECOVERY_RECORD}" \
            "CAREQUEUE_PRE_UPGRADE_BACKUP"
    )"

    ROLLBACK_APPLICATION_ARCHIVE="$(
        read_env_value \
            "${ROLLBACK_RECOVERY_RECORD}" \
            "CAREQUEUE_PRE_UPGRADE_APPLICATION"
    )"

    ROLLBACK_APPLICATION_SHA256="$(
        read_env_value \
            "${ROLLBACK_RECOVERY_RECORD}" \
            "CAREQUEUE_PRE_UPGRADE_APPLICATION_SHA256"
    )"

    if [[ -z "${ROLLBACK_BACKUP_PATH}" ]]; then
        fail \
            "The failed upgrade recovery record does not contain a pre-upgrade backup path."
    fi

    if [[ ! -f "${ROLLBACK_BACKUP_PATH}" ]]; then
        fail \
            "The pre-upgrade rollback backup does not exist: ${ROLLBACK_BACKUP_PATH}"
    fi

    if [[ ! -s "${ROLLBACK_BACKUP_PATH}" ]]; then
        fail \
            "The pre-upgrade rollback backup is empty: ${ROLLBACK_BACKUP_PATH}"
    fi

    if [[ -z "${ROLLBACK_APPLICATION_ARCHIVE}" ]]; then
        fail \
            "The failed upgrade recovery record does not contain a pre-upgrade application archive."
    fi

    if [[ ! -f "${ROLLBACK_APPLICATION_ARCHIVE}" ]]; then
        fail \
            "The pre-upgrade application archive does not exist: ${ROLLBACK_APPLICATION_ARCHIVE}"
    fi

    if [[ ! -s "${ROLLBACK_APPLICATION_ARCHIVE}" ]]; then
        fail \
            "The pre-upgrade application archive is empty: ${ROLLBACK_APPLICATION_ARCHIVE}"
    fi

    if [[ ! "${ROLLBACK_APPLICATION_SHA256}" =~ ^[0-9a-f]{64}$ ]]; then
        fail \
            "The failed upgrade recovery record contains an invalid application archive checksum."
    fi

    local calculated_application_sha256

    calculated_application_sha256="$(
        sha256sum "${ROLLBACK_APPLICATION_ARCHIVE}" |
            awk '{print $1}'
    )"

    if [[ "${calculated_application_sha256}" != "${ROLLBACK_APPLICATION_SHA256}" ]]; then
        fail \
            "Pre-upgrade application archive checksum verification failed."
    fi

    printf \
        'Rollback recovery record: %s\n' \
        "${ROLLBACK_RECOVERY_RECORD}"

    printf \
        'Previous CareQueue version: %s\n' \
        "${ROLLBACK_PREVIOUS_VERSION:-unknown}"

    printf \
        'Failed incoming version: %s\n' \
        "${ROLLBACK_INCOMING_VERSION:-unknown}"

    printf \
        'Pre-upgrade backup: %s\n' \
        "${ROLLBACK_BACKUP_PATH}"

    printf \
        'Pre-upgrade application: %s\n' \
        "${ROLLBACK_APPLICATION_ARCHIVE}"

    printf \
        'Verified application SHA256: %s\n' \
        "${ROLLBACK_APPLICATION_SHA256}"
}

stage_verified_rollback_application() {
    local staging_parent

    if [[ "${MODE}" != "rollback" ]]; then
        return
    fi

    staging_parent="${DATA_DIRECTORY}/recovery/application-staging"

    mkdir -p "${staging_parent}"
    chmod 0750 "${staging_parent}"

    ROLLBACK_APPLICATION_STAGING_DIRECTORY="$(
        mktemp \
            --directory \
            "${staging_parent}/rollback-application.XXXXXX"
    )"

    chmod 0750 "${ROLLBACK_APPLICATION_STAGING_DIRECTORY}"

    printf '%s\n' \
        "Extracting verified pre-upgrade application payload..."

    if ! tar \
        --extract \
        --gzip \
        --file "${ROLLBACK_APPLICATION_ARCHIVE}" \
        --directory "${ROLLBACK_APPLICATION_STAGING_DIRECTORY}"; then

        rm -rf "${ROLLBACK_APPLICATION_STAGING_DIRECTORY}"
        ROLLBACK_APPLICATION_STAGING_DIRECTORY=""

        fail \
            "Unable to extract the verified pre-upgrade application archive."
    fi

    ROLLBACK_APPLICATION_STAGING_ROOT="${ROLLBACK_APPLICATION_STAGING_DIRECTORY}"

    if [[ ! -d "${ROLLBACK_APPLICATION_STAGING_ROOT}/backend" ]] \
        || [[ ! -d "${ROLLBACK_APPLICATION_STAGING_ROOT}/frontend" ]] \
        || [[ ! -d "${ROLLBACK_APPLICATION_STAGING_ROOT}/deployment" ]]; then

        rm -rf "${ROLLBACK_APPLICATION_STAGING_DIRECTORY}"
        ROLLBACK_APPLICATION_STAGING_DIRECTORY=""
        ROLLBACK_APPLICATION_STAGING_ROOT=""

        fail \
            "The staged rollback application payload is missing required application directories."
    fi

    if [[ -e "${ROLLBACK_APPLICATION_STAGING_ROOT}/backend/.venv" ]]; then
        rm -rf "${ROLLBACK_APPLICATION_STAGING_DIRECTORY}"
        ROLLBACK_APPLICATION_STAGING_DIRECTORY=""
        ROLLBACK_APPLICATION_STAGING_ROOT=""

        fail \
            "The rollback application payload unexpectedly contains a Python virtual environment."
    fi

    printf \
        'Validated staged rollback application: %s\n' \
        "${ROLLBACK_APPLICATION_STAGING_ROOT}"
}

preserve_failed_application_before_rollback() {
    local archive_name
    local calculated_checksum
    local checksum_path

    if [[ "${MODE}" != "rollback" ]]; then
        return
    fi

    if [[ ! -d "${INSTALL_DIRECTORY}/backend" ]] \
        || [[ ! -d "${INSTALL_DIRECTORY}/frontend" ]] \
        || [[ ! -d "${INSTALL_DIRECTORY}/deployment" ]]; then
        fail \
            "Cannot preserve the failed CareQueue application because required application directories are missing."
    fi

    mkdir -p "${UPGRADE_APPLICATION_RECOVERY_DIRECTORY}"
    chmod 0750 "${UPGRADE_APPLICATION_RECOVERY_DIRECTORY}"

    archive_name="$(
        printf \
            'carequeue-failed-application-%s.tar.gz' \
            "${ROLLBACK_INCOMING_VERSION:-unknown}"
    )"

    FAILED_APPLICATION_ARCHIVE="${
        UPGRADE_APPLICATION_RECOVERY_DIRECTORY
    }/${archive_name}"

    checksum_path="${FAILED_APPLICATION_ARCHIVE}.sha256"

    printf '%s\n' \
        "Preserving the failed application before rollback..."

    rm -f \
        "${FAILED_APPLICATION_ARCHIVE}" \
        "${checksum_path}"

    tar \
        --create \
        --gzip \
        --file "${FAILED_APPLICATION_ARCHIVE}" \
        --directory "${INSTALL_DIRECTORY}" \
        --exclude='backend/.venv' \
        backend \
        frontend \
        deployment

    if [[ ! -s "${FAILED_APPLICATION_ARCHIVE}" ]]; then
        fail \
            "The failed application archive was not created successfully."
    fi

    FAILED_APPLICATION_SHA256="$(
        sha256sum "${FAILED_APPLICATION_ARCHIVE}" |
            awk '{print $1}'
    )"

    if [[ ! "${FAILED_APPLICATION_SHA256}" =~ ^[0-9a-f]{64}$ ]]; then
        fail \
            "Unable to calculate the failed application archive checksum."
    fi

    printf '%s  %s\n' \
        "${FAILED_APPLICATION_SHA256}" \
        "$(basename "${FAILED_APPLICATION_ARCHIVE}")" \
        > "${checksum_path}"

    chmod 0640 \
        "${FAILED_APPLICATION_ARCHIVE}" \
        "${checksum_path}"

    calculated_checksum="$(
        sha256sum "${FAILED_APPLICATION_ARCHIVE}" |
            awk '{print $1}'
    )"

    if [[ "${calculated_checksum}" != "${FAILED_APPLICATION_SHA256}" ]]; then
        fail \
            "Failed application archive checksum verification failed."
    fi

    printf \
        'Verified failed application payload: %s\n' \
        "${FAILED_APPLICATION_ARCHIVE}"

    printf \
        'Failed application SHA256: %s\n' \
        "${FAILED_APPLICATION_SHA256}"
}

record_failed_application_for_rollback() {
    local temporary_record

    if [[ "${MODE}" != "rollback" ]]; then
        return
    fi

    if [[ -z "${ROLLBACK_RECOVERY_RECORD}" ]] \
        || [[ ! -f "${ROLLBACK_RECOVERY_RECORD}" ]]; then
        fail \
            "Cannot record the failed application because the rollback recovery record is unavailable."
    fi

    if [[ -z "${FAILED_APPLICATION_ARCHIVE}" ]] \
        || [[ -z "${FAILED_APPLICATION_SHA256}" ]]; then
        fail \
            "Cannot record the failed application because its verified archive metadata is unavailable."
    fi

    temporary_record="${ROLLBACK_RECOVERY_RECORD}.tmp"

    awk \
        -v archive_path="${FAILED_APPLICATION_ARCHIVE}" \
        -v archive_sha256="${FAILED_APPLICATION_SHA256}" \
        '
        BEGIN {
            wrote_archive = 0
            wrote_checksum = 0
        }
        /^CAREQUEUE_FAILED_APPLICATION=/ {
            print "CAREQUEUE_FAILED_APPLICATION=" archive_path
            wrote_archive = 1
            next
        }
        /^CAREQUEUE_FAILED_APPLICATION_SHA256=/ {
            print "CAREQUEUE_FAILED_APPLICATION_SHA256=" archive_sha256
            wrote_checksum = 1
            next
        }
        {
            print
        }
        END {
            if (!wrote_archive) {
                print "CAREQUEUE_FAILED_APPLICATION=" archive_path
            }

            if (!wrote_checksum) {
                print "CAREQUEUE_FAILED_APPLICATION_SHA256=" archive_sha256
            }
        }
        ' \
        "${ROLLBACK_RECOVERY_RECORD}" \
        > "${temporary_record}"

    chmod 0640 "${temporary_record}"
    mv -f "${temporary_record}" "${ROLLBACK_RECOVERY_RECORD}"
}

prepare_failed_upgrade_rollback() {
    local restore_script

    if [[ "${MODE}" != "rollback" ]]; then
        return
    fi

    restore_script="${INSTALL_DIRECTORY}/backend/scripts/restore_encrypted_backup.py"

    if [[ ! -f "${restore_script}" ]]; then
        fail \
            "CareQueue rollback requires the installed restore script: ${restore_script}"
    fi

    printf 'Staging the verified pre-upgrade database backup for recovery...\n'

    if ! "${INSTALL_DIRECTORY}/backend/.venv/bin/python" \
        "${restore_script}" \
        "${ROLLBACK_BACKUP_PATH}"; then
        fail \
            "CareQueue rollback preparation failed while staging the pre-upgrade backup."
    fi

    update_rollback_recovery_status "rollback_staged"

    printf '%s\n' \
        "Rollback database preparation completed."

    printf '%s\n' \
        "Upgrade recovery status: rollback_staged"

    printf '%s\n' \
        "The active database has not been replaced."

    printf '%s\n' \
        "Complete recovery activation using the staged CareQueue recovery workflow."
}

activate_failed_upgrade_rollback() {
    local activation_script

    if [[ "${MODE}" != "rollback" ]]; then
        return
    fi

    activation_script="${
        INSTALL_DIRECTORY
    }/backend/scripts/activate_staged_recovery.py"

    if [[ ! -f "${activation_script}" ]]; then
        fail \
            "CareQueue rollback requires the installed recovery activation script: ${activation_script}"
    fi

    if [[ ! -x "${INSTALL_DIRECTORY}/backend/.venv/bin/python" ]]; then
        fail \
            "CareQueue rollback requires the installed Python environment."
    fi

    printf '%s\n' \
        "Stopping the CareQueue API before rollback activation..."

    if ! systemctl stop carequeue-api.service; then
        fail \
            "CareQueue rollback could not stop carequeue-api.service."
    fi

    printf '%s\n' \
        "Activating the staged pre-upgrade database..."

    if ! systemd-run \
        --wait \
        --pipe \
        --collect \
        --property="EnvironmentFile=${CONFIG_DIRECTORY}/carequeue.env" \
        --working-directory="${INSTALL_DIRECTORY}/backend" \
        "${INSTALL_DIRECTORY}/backend/.venv/bin/python" \
        "${activation_script}" \
        --service-name carequeue-api.service \
        --database-path "${DATA_DIRECTORY}/data/auth_tracker.sqlcipher.db" \
        --backup-directory "${BACKUP_DIRECTORY}" \
        --restore-directory "${DATA_DIRECTORY}/restores"; then

        printf '%s\n' \
            "Rollback activation did not complete successfully."

        printf '%s\n' \
            "CareQueue API remains stopped for safety."

        fail \
            "Review the recovery output before attempting another recovery operation."
    fi

    update_rollback_recovery_status "rollback_activated"

    printf '%s\n' \
        "Rollback database activation completed."

    printf '%s\n' \
        "Starting the CareQueue API..."

    if ! systemctl start carequeue-api.service; then
        fail \
            "Rollback activation completed, but carequeue-api.service could not be started."
    fi

    restore_previous_install_state_version
    update_rollback_recovery_status "rollback_completed"

    printf '%s\n' \
        "CareQueue API started after rollback activation."

    printf '%s\n' \
        "Upgrade recovery status: rollback_completed"
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
    resolve_failed_upgrade_recovery_record
    prepare_logging
    print_header
    create_verified_pre_upgrade_backup
    create_verified_pre_upgrade_application_archive
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

        rollback)
            printf 'Preparing CareQueue rollback from the latest failed upgrade...\n'
            stage_verified_rollback_application
            preserve_failed_application_before_rollback
            record_failed_application_for_rollback
            prepare_failed_upgrade_rollback
            activate_failed_upgrade_rollback
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