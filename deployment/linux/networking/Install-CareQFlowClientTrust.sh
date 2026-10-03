#!/usr/bin/env bash

set -Eeuo pipefail

CERTIFICATE_PATH=""
EXPECTED_FINGERPRINT=""
APPLICATION_ORIGIN=""

CAREQUEUE_HOSTNAME="careqflow.local"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail \
            "Installing the CareQFlow client trust certificate " \
            "must be run as root."
    fi
}

parse_arguments() {
    while (( $# > 0 )); do
        case "$1" in
            --certificate)
                [[ $# -ge 2 ]] \
                    || fail "--certificate requires a value."

                CERTIFICATE_PATH="$2"
                shift 2
                ;;

            --expected-fingerprint)
                [[ $# -ge 2 ]] \
                    || fail "--expected-fingerprint requires a value."

                EXPECTED_FINGERPRINT="$2"
                shift 2
                ;;

            --application-origin)
                [[ $# -ge 2 ]] \
                    || fail "--application-origin requires a value."

                APPLICATION_ORIGIN="$2"
                shift 2
                ;;

            *)
                fail "Unknown client trust option: $1"
                ;;
        esac
    done

    [[ -n "${CERTIFICATE_PATH}" ]] \
        || fail "--certificate is required."

    [[ -n "${EXPECTED_FINGERPRINT}" ]] \
        || fail "--expected-fingerprint is required."

    [[ -n "${APPLICATION_ORIGIN}" ]] \
        || fail "--application-origin is required."
}

require_dependencies() {
    command -v openssl >/dev/null 2>&1 \
        || fail "OpenSSL is required to install CareQFlow client trust."

    command -v python3 >/dev/null 2>&1 \
        || fail "Python 3 is required to configure the CareQFlow hostname."
}

validate_application_origin() {
    CAREQUEUE_SERVER_IP="$(
        python3 - "${APPLICATION_ORIGIN}" <<'PY'
import ipaddress
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

if port not in {None, 443}:
    raise SystemExit(1)

try:
    address = ipaddress.IPv4Address(parsed.hostname)
except ipaddress.AddressValueError:
    raise SystemExit(1)

supported_networks = (
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("100.64.0.0/10"),
)

if not any(address in network for network in supported_networks):
    raise SystemExit(1)

print(address)
PY
    )" || fail \
        "CareQFlow client hostname configuration requires an HTTPS " \
        "RFC1918 or Tailscale IPv4 application origin on port 443."

    APPLICATION_ORIGIN="${APPLICATION_ORIGIN%/}"
}

normalize_fingerprint() {
    printf '%s' "$1" |
        tr -d ':[:space:]' |
        tr '[:lower:]' '[:upper:]'
}

validate_certificate() {
    local normalized_expected
    local actual_fingerprint
    local normalized_actual

    if [[ ! -f "${CERTIFICATE_PATH}" ]]; then
        fail \
            "The CareQFlow client trust certificate was not found: " \
            "${CERTIFICATE_PATH}"
    fi

    if grep -q "PRIVATE KEY" "${CERTIFICATE_PATH}"; then
        fail \
            "The CareQFlow client trust certificate unexpectedly " \
            "contains private key material."
    fi

    openssl x509 \
        -in "${CERTIFICATE_PATH}" \
        -noout \
        >/dev/null 2>&1 \
        || fail \
            "The CareQFlow client trust certificate is not a valid " \
            "X.509 certificate."

    openssl x509 \
        -in "${CERTIFICATE_PATH}" \
        -noout \
        -text |
        grep -q "CA:TRUE" \
        || fail \
            "The supplied CareQFlow certificate is not marked " \
            "as a certificate authority."

    openssl x509 \
        -in "${CERTIFICATE_PATH}" \
        -checkend 0 \
        -noout \
        >/dev/null 2>&1 \
        || fail \
            "The CareQFlow client trust certificate is expired or " \
            "is not currently valid."

    openssl verify \
        -CAfile "${CERTIFICATE_PATH}" \
        "${CERTIFICATE_PATH}" \
        >/dev/null 2>&1 \
        || fail \
            "The supplied CareQFlow certificate could not verify " \
            "itself as a trusted root."

    normalized_expected="$(
        normalize_fingerprint \
            "${EXPECTED_FINGERPRINT}"
    )"

    if [[ ! "${normalized_expected}" =~ ^[0-9A-F]{64}$ ]]; then
        fail \
            "Expected fingerprint must be a complete SHA-256 " \
            "certificate fingerprint."
    fi

    actual_fingerprint="$(
        openssl x509 \
            -in "${CERTIFICATE_PATH}" \
            -noout \
            -fingerprint \
            -sha256 |
            sed \
                -e 's/^sha256 Fingerprint=//' \
                -e 's/^SHA256 Fingerprint=//'
    )"

    normalized_actual="$(
        normalize_fingerprint \
            "${actual_fingerprint}"
    )"

    if [[ "${normalized_actual}" != "${normalized_expected}" ]]; then
        fail \
            "The CareQFlow certificate SHA-256 fingerprint does not " \
            "match the expected fingerprint. Do not trust this certificate."
    fi

    VERIFIED_FINGERPRINT="${actual_fingerprint}"
}

install_certificate_trust() {
    local destination

    if command -v update-ca-certificates >/dev/null 2>&1; then
        destination="/usr/local/share/ca-certificates/CareQFlow-Root-CA.crt"

        install \
            -o root \
            -g root \
            -m 0644 \
            "${CERTIFICATE_PATH}" \
            "${destination}"

        update-ca-certificates

        printf '%s\n' \
            "CareQFlow root certificate installed using update-ca-certificates."

        return
    fi

    if command -v update-ca-trust >/dev/null 2>&1; then
        destination="/etc/pki/ca-trust/source/anchors/CareQFlow-Root-CA.crt"

        install \
            -D \
            -o root \
            -g root \
            -m 0644 \
            "${CERTIFICATE_PATH}" \
            "${destination}"

        update-ca-trust extract

        printf '%s\n' \
            "CareQFlow root certificate installed using update-ca-trust."

        return
    fi

    fail \
        "No supported system certificate trust utility was found. " \
        "CareQFlow supports update-ca-certificates or update-ca-trust."
}

configure_client_hostname() {
    local hosts_file
    local temporary_file

    hosts_file="/etc/hosts"
    temporary_file="$(mktemp)"

    python3 \
        - "${hosts_file}" \
        "${temporary_file}" \
        "${CAREQUEUE_SERVER_IP}" \
        "${CAREQUEUE_HOSTNAME}" <<'PY'
from pathlib import Path
import sys

source_path = Path(sys.argv[1])
destination_path = Path(sys.argv[2])
server_ip = sys.argv[3]
hostname = sys.argv[4]

output_lines: list[str] = []

for original_line in source_path.read_text(
    encoding="utf-8",
).splitlines():
    content, separator, comment = original_line.partition("#")
    fields = content.split()

    if len(fields) >= 2 and hostname in fields[1:]:
        remaining_hosts = [
            value
            for value in fields[1:]
            if value != hostname
        ]

        if remaining_hosts:
            rebuilt = " ".join(
                [fields[0], *remaining_hosts]
            )

            if separator:
                rebuilt += f" #{comment}"

            output_lines.append(rebuilt)

        continue

    output_lines.append(original_line)

output_lines.append(
    f"{server_ip} {hostname} # CareQFlow"
)

destination_path.write_text(
    "\n".join(output_lines) + "\n",
    encoding="utf-8",
)
PY

    cat "${temporary_file}" > "${hosts_file}"
    rm -f "${temporary_file}"

    printf \
        'CareQFlow hostname configured: %s -> %s\n' \
        "${CAREQUEUE_HOSTNAME}" \
        "${CAREQUEUE_SERVER_IP}"
}

main() {
    require_root
    parse_arguments "$@"
    require_dependencies
    validate_application_origin
    validate_certificate
    install_certificate_trust
    configure_client_hostname

    printf '\n'
    printf '%s\n' \
        "CareQFlow client trust installed successfully."

    printf 'SHA-256 fingerprint: %s\n' \
        "${VERIFIED_FINGERPRINT}"

    printf 'Friendly URL: https://%s\n' \
        "${CAREQUEUE_HOSTNAME}"

    printf 'Server URL: %s\n' \
        "${APPLICATION_ORIGIN}"
}

main "$@"