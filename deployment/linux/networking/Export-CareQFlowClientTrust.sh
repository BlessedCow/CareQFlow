#!/usr/bin/env bash

set -Eeuo pipefail

DATA_DIRECTORY="${DATA_DIRECTORY:-/var/lib/carequeue}"
OUTPUT_DIRECTORY=""
APPLICATION_ORIGIN=""

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        fail "CareQFlow client trust export must be run as root."
    fi
}

parse_arguments() {
    while (( $# > 0 )); do
        case "$1" in
            --data-directory)
                [[ $# -ge 2 ]] \
                    || fail "--data-directory requires a value."

                DATA_DIRECTORY="$2"
                shift 2
                ;;

            --output-directory)
                [[ $# -ge 2 ]] \
                    || fail "--output-directory requires a value."

                OUTPUT_DIRECTORY="$2"
                shift 2
                ;;

            --application-origin)
                [[ $# -ge 2 ]] \
                    || fail "--application-origin requires a value."

                APPLICATION_ORIGIN="$2"
                shift 2
                ;;

            *)
                fail "Unknown client trust export option: $1"
                ;;
        esac
    done

    if [[ -z "${OUTPUT_DIRECTORY}" ]]; then
        OUTPUT_DIRECTORY="${DATA_DIRECTORY}/ClientTrust"
    fi
}

validate_application_origin() {
    if ! python3 - "${APPLICATION_ORIGIN}" <<'PY'
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
PY
    then
        fail \
            "CareQFlow client onboarding requires an HTTPS " \
            "RFC1918 or Tailscale IPv4 application origin on port 443."
    fi

    APPLICATION_ORIGIN="${APPLICATION_ORIGIN%/}"
}

require_export_dependencies() {
    command -v openssl >/dev/null 2>&1 \
        || fail "OpenSSL is required to export CareQFlow client trust."

    command -v sha256sum >/dev/null 2>&1 \
        || fail "sha256sum is required to export CareQFlow client trust."
}

validate_root_certificate() {
    local certificate_path="$1"

    if grep -q "PRIVATE KEY" "${certificate_path}"; then
        fail \
            "The CareQFlow client trust export refused a file " \
            "containing private key material."
    fi

    openssl x509 \
        -in "${certificate_path}" \
        -noout \
        >/dev/null 2>&1 \
        || fail "The CareQFlow Caddy root certificate is not a valid X.509 certificate."

    openssl x509 \
        -in "${certificate_path}" \
        -noout \
        -text |
        grep -q "CA:TRUE" \
        || fail \
            "The CareQFlow client trust certificate is not marked " \
            "as a certificate authority."

    openssl x509 \
        -in "${certificate_path}" \
        -checkend 0 \
        -noout \
        >/dev/null 2>&1 \
        || fail \
            "The CareQFlow root certificate is expired or is not currently valid."

    openssl verify \
        -CAfile "${certificate_path}" \
        "${certificate_path}" \
        >/dev/null 2>&1 \
        || fail \
            "The CareQFlow root certificate could not verify itself " \
            "as a trusted root."
}

get_certificate_fingerprint() {
    local certificate_path="$1"

    openssl x509 \
        -in "${certificate_path}" \
        -noout \
        -fingerprint \
        -sha256 |
        sed \
            -e 's/^sha256 Fingerprint=//' \
            -e 's/^SHA256 Fingerprint=//'
}

create_client_trust_package() {
    local root_certificate_path
    local exported_certificate_path
    local client_installer_source
    local client_installer_destination
    local onboarding_path
    local verification_path
    local file_hash
    local certificate_fingerprint

    root_certificate_path="${DATA_DIRECTORY}/caddy/data/caddy/pki/authorities/local/root.crt"

    client_installer_source="$(
        cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
        pwd
    )/Install-CareQFlowClientTrust.sh"

    if [[ ! -f "${root_certificate_path}" ]]; then
        fail \
            "The CareQFlow Caddy root certificate was not found: " \
            "${root_certificate_path}"
    fi

    if [[ ! -f "${client_installer_source}" ]]; then
        fail \
            "The CareQFlow Linux client trust installer was not found: " \
            "${client_installer_source}"
    fi

    validate_root_certificate "${root_certificate_path}"

    rm -rf "${OUTPUT_DIRECTORY}"

    install \
        -d \
        -o root \
        -g root \
        -m 0755 \
        "${OUTPUT_DIRECTORY}"

    exported_certificate_path="${OUTPUT_DIRECTORY}/CareQFlow-Root-CA.crt"

    client_installer_destination="${OUTPUT_DIRECTORY}/Install-CareQFlowClientTrust.sh"

    onboarding_path="${OUTPUT_DIRECTORY}/CLIENT-ONBOARDING.txt"

    verification_path="${OUTPUT_DIRECTORY}/SHA256SUMS.txt"

    install \
        -o root \
        -g root \
        -m 0644 \
        "${root_certificate_path}" \
        "${exported_certificate_path}"

    install \
        -o root \
        -g root \
        -m 0644 \
        "${client_installer_source}" \
        "${client_installer_destination}"

    validate_root_certificate "${exported_certificate_path}"

    file_hash="$(
        sha256sum "${exported_certificate_path}" |
            awk '{print $1}'
    )"

    certificate_fingerprint="$(
        get_certificate_fingerprint \
            "${exported_certificate_path}"
    )"

    cat > "${verification_path}" <<EOF
CareQFlow Client Trust Certificate

File: CareQFlow-Root-CA.crt
File SHA-256: ${file_hash}
Certificate SHA-256 fingerprint: ${certificate_fingerprint}
EOF

    cat > "${onboarding_path}" <<EOF
CareQFlow Secure LAN Client Onboarding

CareQFlow server URL:
${APPLICATION_ORIGIN}

Friendly client URL:
https://careqflow.local

Before trusting the included certificate, verify its
SHA-256 fingerprint with the CareQFlow administrator
using a separate trusted method.

Certificate SHA-256 fingerprint:
${certificate_fingerprint}

Linux client:
1. Copy this entire ClientTrust folder to the authorized computer.
2. Open a terminal in the copied folder.
3. Verify the fingerprint above using a separate trusted method.
4. Run:

   sudo bash ./Install-CareQFlowClientTrust.sh \
       --certificate ./CareQFlow-Root-CA.crt \
       --expected-fingerprint "${certificate_fingerprint}" \
       --application-origin "${APPLICATION_ORIGIN}"

5. Open:

   https://careqflow.local

The server IP URL also remains available:

   ${APPLICATION_ORIGIN}

Security:
- Do not install the certificate if the fingerprint is different.
- Do not expose CareQFlow using router port forwarding.
- Secure LAN is intended only for trusted private networks.
- The CareQFlow backend remains inaccessible directly.
EOF

    chmod 0644 \
        "${exported_certificate_path}" \
        "${client_installer_destination}" \
        "${onboarding_path}" \
        "${verification_path}"

    if find "${OUTPUT_DIRECTORY}" \
        -type f \
        \( \
            -name '*.key' \
            -o -name '*.pfx' \
            -o -name '*.p12' \
            -o -name '*.pem' \
        \) |
        grep -q .
    then
        fail \
            "Private key material was detected in the CareQFlow " \
            "client trust export directory."
    fi

    if grep -R -q \
        --include='*' \
        "BEGIN .*PRIVATE KEY" \
        "${OUTPUT_DIRECTORY}"
    then
        fail \
            "Private key content was detected in the CareQFlow " \
            "client trust export directory."
    fi

    printf '%s\n' \
        "CareQFlow client trust package created successfully."

    printf 'Certificate: %s\n' \
        "${exported_certificate_path}"

    printf 'Verification: %s\n' \
        "${verification_path}"

    printf 'Onboarding instructions: %s\n' \
        "${onboarding_path}"

    printf 'Linux trust installer: %s\n' \
        "${client_installer_destination}"

    printf 'CareQFlow URL: %s\n' \
        "${APPLICATION_ORIGIN}"

    printf 'Certificate SHA-256 fingerprint: %s\n' \
        "${certificate_fingerprint}"
}

main() {
    require_root
    parse_arguments "$@"
    validate_application_origin
    require_export_dependencies
    create_client_trust_package
}

main "$@"