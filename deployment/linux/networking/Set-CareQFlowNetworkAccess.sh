#!/usr/bin/env bash

set -Eeuo pipefail

NETWORK_MODE=""
APPLICATION_ORIGIN=""
CONFIG_DIRECTORY="${CONFIG_DIRECTORY:-/etc/carequeue}"

STATE_FILE=""

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail "CareQFlow network configuration must be run as root."
    fi
}

parse_arguments() {
    while (( $# > 0 )); do
        case "$1" in
            --network-mode)
                [[ $# -ge 2 ]] \
                    || fail "--network-mode requires a value."

                NETWORK_MODE="$2"
                shift 2
                ;;

            --application-origin)
                [[ $# -ge 2 ]] \
                    || fail "--application-origin requires a value."

                APPLICATION_ORIGIN="$2"
                shift 2
                ;;

            --config-directory)
                [[ $# -ge 2 ]] \
                    || fail "--config-directory requires a value."

                CONFIG_DIRECTORY="$2"
                shift 2
                ;;

            *)
                fail "Unknown network configuration option: $1"
                ;;
        esac
    done

    STATE_FILE="${CONFIG_DIRECTORY}/network-access.env"
}

validate_network_mode() {
    case "${NETWORK_MODE}" in
        LocalOnly|SecureLan)
            ;;
        *)
            fail \
                "Network mode must be LocalOnly or SecureLan."
            ;;
    esac
}

read_state_value() {
    local key="$1"

    if [[ ! -f "${STATE_FILE}" ]]; then
        return
    fi

    awk \
        -F= \
        -v requested_key="${key}" \
        '$1 == requested_key {
            sub(/^[^=]*=/, "", $0)
            print $0
            exit
        }' \
        "${STATE_FILE}"
}

remove_previous_ufw_rule() {
    local subnet="$1"

    if [[ -z "${subnet}" ]] || ! command -v ufw >/dev/null 2>&1; then
        return
    fi

    ufw --force delete \
        allow \
        from "${subnet}" \
        to any \
        port 443 \
        proto tcp \
        >/dev/null 2>&1 || true
}

remove_previous_firewalld_rule() {
    local zone="$1"
    local rule="$2"

    if [[ -z "${zone}" || -z "${rule}" ]]; then
        return
    fi

    if command -v firewall-cmd >/dev/null 2>&1 \
        && firewall-cmd --state >/dev/null 2>&1
    then
        firewall-cmd \
            --permanent \
            --zone="${zone}" \
            --remove-rich-rule="${rule}" \
            >/dev/null 2>&1 || true

        firewall-cmd --reload >/dev/null 2>&1 || true
        return
    fi

    if command -v firewall-offline-cmd >/dev/null 2>&1; then
        firewall-offline-cmd \
            --zone="${zone}" \
            --remove-rich-rule="${rule}" \
            >/dev/null 2>&1 || true
    fi
}

remove_previous_managed_rule() {
    local previous_manager
    local previous_subnet
    local previous_zone
    local previous_rule

    previous_manager="$(
        read_state_value "CAREQUEUE_FIREWALL_MANAGER"
    )"

    previous_subnet="$(
        read_state_value "CAREQUEUE_FIREWALL_SUBNET"
    )"

    previous_zone="$(
        read_state_value "CAREQUEUE_FIREWALL_ZONE"
    )"

    previous_rule="$(
        read_state_value "CAREQUEUE_FIREWALL_RULE"
    )"

    case "${previous_manager}" in
        ufw)
            remove_previous_ufw_rule \
                "${previous_subnet}"
            ;;

        firewalld)
            remove_previous_firewalld_rule \
                "${previous_zone}" \
                "${previous_rule}"
            ;;
    esac
}

resolve_secure_lan_interface() {
    local application_ip
    local record
    local interface
    local cidr

    application_ip="$(
        python3 - "${APPLICATION_ORIGIN}" <<'PY'
import ipaddress
import sys
from urllib.parse import urlsplit

parsed = urlsplit(sys.argv[1].strip())

try:
    address = ipaddress.IPv4Address(parsed.hostname or "")
except ipaddress.AddressValueError:
    raise SystemExit(1)

print(address)
PY
    )" || fail "Unable to resolve the Secure LAN IPv4 address."

    while IFS= read -r record; do
        interface="$(
            awk '{print $2}' <<< "${record}"
        )"

        cidr="$(
            awk '{print $4}' <<< "${record}"
        )"

        if [[ "${cidr%%/*}" == "${application_ip}" ]]; then
            SECURE_LAN_INTERFACE="${interface}"
            SECURE_LAN_CIDR="${cidr}"

            SECURE_LAN_SUBNET="$(
                python3 - "${cidr}" <<'PY'
import ipaddress
import sys

print(
    ipaddress.ip_interface(
        sys.argv[1]
    ).network
)
PY
            )"

            return
        fi
    done < <(
        ip -o -4 addr show scope global
    )

    fail \
        "The selected Secure LAN address is not assigned " \
        "to a local network interface."
}

detect_active_firewall() {
    if command -v ufw >/dev/null 2>&1 \
        && ufw status 2>/dev/null |
            grep -q '^Status: active$'
    then
        FIREWALL_MANAGER="ufw"
        return
    fi

    if command -v firewall-cmd >/dev/null 2>&1 \
        && firewall-cmd --state >/dev/null 2>&1
    then
        FIREWALL_MANAGER="firewalld"
        return
    fi

    fail \
        "SecureLan requires an active UFW or firewalld firewall. " \
        "CareQFlow will not expose HTTPS without an active firewall boundary."
}

configure_ufw() {
    ufw allow \
        from "${SECURE_LAN_SUBNET}" \
        to any \
        port 443 \
        proto tcp \
        comment "CareQFlow Secure LAN HTTPS"

    FIREWALL_ZONE=""
    FIREWALL_RULE=""
}

configure_firewalld() {
    FIREWALL_ZONE="$(
        firewall-cmd \
            --get-zone-of-interface="${SECURE_LAN_INTERFACE}" \
            2>/dev/null || true
    )"

    if [[ -z "${FIREWALL_ZONE}" \
        || "${FIREWALL_ZONE}" == "no zone" ]]
    then
        FIREWALL_ZONE="$(
            firewall-cmd --get-default-zone
        )"
    fi

    FIREWALL_RULE="$(
        printf \
            'rule family="ipv4" source address="%s" port port="443" protocol="tcp" accept' \
            "${SECURE_LAN_SUBNET}"
    )"

    firewall-cmd \
        --permanent \
        --zone="${FIREWALL_ZONE}" \
        --add-rich-rule="${FIREWALL_RULE}"

    firewall-cmd --reload
}

write_state() {
    install \
        -d \
        -o root \
        -g carequeue \
        -m 0710 \
        "${CONFIG_DIRECTORY}"

    cat > "${STATE_FILE}" <<EOF
CAREQUEUE_NETWORK_ACCESS_SCHEMA=1
CAREQUEUE_NETWORK_MODE=${NETWORK_MODE}
CAREQUEUE_FIREWALL_MANAGER=${FIREWALL_MANAGER:-}
CAREQUEUE_FIREWALL_INTERFACE=${SECURE_LAN_INTERFACE:-}
CAREQUEUE_FIREWALL_SUBNET=${SECURE_LAN_SUBNET:-}
CAREQUEUE_FIREWALL_ZONE=${FIREWALL_ZONE:-}
CAREQUEUE_FIREWALL_RULE=${FIREWALL_RULE:-}
EOF

    chown root:root "${STATE_FILE}"
    chmod 0640 "${STATE_FILE}"
}

configure_network_access() {
    remove_previous_managed_rule

    if [[ "${NETWORK_MODE}" == "LocalOnly" ]]; then
        FIREWALL_MANAGER=""
        SECURE_LAN_INTERFACE=""
        SECURE_LAN_SUBNET=""
        FIREWALL_ZONE=""
        FIREWALL_RULE=""

        write_state

        printf '%s\n' \
            "CareQFlow Secure LAN firewall access is disabled."

        return
    fi

    if [[ -z "${APPLICATION_ORIGIN}" ]]; then
        fail \
            "SecureLan requires --application-origin."
    fi

    command -v ip >/dev/null 2>&1 \
        || fail "The ip command is required for SecureLan."

    resolve_secure_lan_interface
    detect_active_firewall

    case "${FIREWALL_MANAGER}" in
        ufw)
            configure_ufw
            ;;

        firewalld)
            configure_firewalld
            ;;

        *)
            fail "Unsupported firewall manager."
            ;;
    esac

    write_state

    printf \
        'CareQFlow Secure LAN HTTPS enabled for %s on TCP 443 using %s.\n' \
        "${SECURE_LAN_SUBNET}" \
        "${FIREWALL_MANAGER}"
}

main() {
    require_root
    parse_arguments "$@"
    validate_network_mode
    configure_network_access
}

main "$@"